import threading
import time
import traceback

import matplotlib.pyplot as plt
import numpy as np
import solara

from base_agent import MissileAgent
from target_agent import TargetAgent
from model import NavalModel, SwarmMode
from TargetReportingUnit import TargetReportingUnit
from swarm_modes import MissileType # Import MissileType to check agent role

# --- Configuration ---
WIDTH = 250
HEIGHT = 60
NUM_MISSILES = 25 # Increased for better group visibility in Recce Mode
LAUNCH_INTERVAL = 10

# --- Solara Reactive States ---
step_count = solara.reactive(0)
# This is where we define the model with the initial parameters
# The default is setting the the swarm mode set to SPLIT_AXIS for demonstration purposes
# swarm_mode=SwarmMode.SPLIT_AXIS
model = solara.reactive(
    NavalModel(
        width=WIDTH,
        height=HEIGHT,
        num_missiles=NUM_MISSILES,
        launch_interval=LAUNCH_INTERVAL,
        swarm_mode=SwarmMode.SPLIT_AXIS
    )
)
running = solara.reactive(False)
speed_slider = solara.reactive(0.5)

grid_width = model.value.grid.width
grid_height = model.value.grid.height


@solara.component
def MissileGrid():
    _ = step_count.value

    fig, ax = plt.subplots(figsize=(10, 2))
    ax.set_xlim(0, grid_width)
    ax.set_ylim(0, grid_height)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

    for agent in model.value.agents:
        if isinstance(agent, MissileAgent):
            # Determine color based on missile state and type
            if agent.exploded:
                color = "red" # Exploded missiles are red
            elif agent.missile_type == MissileType.SCOUT:
                color = "lightblue" # Scouts are lighter blue
            else:
                color = "blue" # Attackers are darker blue

            if agent.alive and len(agent.trail) > 1:
                xs, ys = zip(*agent.trail)
                ax.plot([x + 0.5 for x in xs], [y + 0.5 for y in ys], color=color, linewidth=1, alpha=0.5)
            if agent.alive:
                ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "o", color=color, markersize=5)
        elif isinstance(agent, TargetAgent):
            ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "s", color="green", markersize=8)
        elif isinstance(agent, TargetReportingUnit):
            ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "^", color="purple", markersize=8)

    return solara.FigureMatplotlib(fig)


@solara.component
def MissileDashboard():
    solara.Title("Naval Missile Simulation")

    def simulation_finished():
        all_missiles_launched = model.value.missile_count >= model.value.num_missiles
        no_active_missiles = not any(isinstance(agent, MissileAgent) and agent.alive for agent in model.value.agents)
        return all_missiles_launched and no_active_missiles

    def auto_step():
        while running.value:
            try:
                if simulation_finished():
                    print("Simulation finished condition met. Stopping auto_step.")
                    running.value = False
                    break
                model.value.step()
                step_count.value += 1
                delay = 2.0 - speed_slider.value * 1.9
                time.sleep(delay)
            except Exception as e:
                print(f"ERROR: Exception caught in auto_step thread: {e}")
                traceback.print_exc()
                running.value = False
                break

    def toggle_play_pause():
        if running.value:
            print("Pausing simulation.")
            running.value = False
        else:
            print("Starting/Resuming simulation.")
            running.value = True
            threading.Thread(target=auto_step, daemon=True).start()

    def step():
        if not simulation_finished():
            print("Performing single step.")
            model.value.step()
            step_count.value += 1
        else:
            print("Cannot step, simulation already finished.")

    def reset():
        print("Resetting simulation.")
        # Ensure reset uses the same configuration as initial setup for consistency
        model.value = NavalModel(
            width=WIDTH,
            height=HEIGHT,
            num_missiles=NUM_MISSILES,
            launch_interval=LAUNCH_INTERVAL,
            swarm_mode=SwarmMode.RECCE # Reset to RECCE mode by default or set to your desired default
        )
        step_count.value = 0
        running.value = False

    with solara.Column():
        solara.Markdown(f"**Step:** {step_count.value}")
        MissileGrid()

        with solara.Row():
            solara.Button("Step", on_click=step)
            solara.Button("Pause" if running.value else "Play", on_click=toggle_play_pause)
            solara.Button("Reset", on_click=reset)

        with solara.Row(style={"alignItems": "center", "gap": "10px"}):
            solara.Markdown("**Speed:**", style={"margin": "0"})

            with solara.Column(style={"width": "200px"}):
                solara.SliderFloat(
                    label=None,
                    value=speed_slider,
                    min=0,
                    max=1,
                    step=0.01,
                    thumb_label=True
                )
                solara.Text(f"{(2.0 - speed_slider.value * 1.9):.2f} sec delay", style={"fontSize": "0.8em", "textAlign": "center"})

            solara.Markdown("Slow", style={"fontSize": "0.8em", "margin": "0"})
            solara.Markdown("Fast", style={"fontSize": "0.8em", "margin": "0"})


@solara.component
def Page():
    MissileDashboard()
