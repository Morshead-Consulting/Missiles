import threading
import time
import traceback # Import traceback for detailed error info

import matplotlib.pyplot as plt
import numpy as np
import solara

from agents import MissileAgent, TargetAgent
from model import NavalModel, SwarmMode
from TargetReportingUnit import TargetReportingUnit

# --- Configuration ---
WIDTH = 250
HEIGHT = 60
NUM_MISSILES = 5
LAUNCH_INTERVAL = 10

# --- Solara Reactive States ---
step_count = solara.reactive(0)
# Initialize the model with specific parameters
model = solara.reactive(
    NavalModel(
        width=WIDTH,
        height=HEIGHT,
        num_missiles=NUM_MISSILES,
        launch_interval=LAUNCH_INTERVAL,
        swarm_mode=SwarmMode.SIMPLE
    )
)
running = solara.reactive(False)
speed_slider = solara.reactive(0.5)

# Get grid dimensions from the initialized model
grid_width = model.value.grid.width
grid_height = model.value.grid.height


@solara.component
def MissileGrid():
    _ = step_count.value # Trigger reactivity

    fig, ax = plt.subplots(figsize=(10, 2))
    ax.set_xlim(0, grid_width)
    ax.set_ylim(0, grid_height)
    ax.set_xticks([]) # Hide x-axis ticks
    ax.set_yticks([]) # Hide y-axis ticks
    ax.set_aspect("equal") # Ensure equal aspect ratio

    # Plot agents and their trails
    for agent in model.value.agents:
        if isinstance(agent, MissileAgent):
            # Determine color based on missile state
            color = "red" if agent.exploded else "blue"
            # Plot missile trail if alive and has moved
            if agent.alive and len(agent.trail) > 1:
                xs, ys = zip(*agent.trail)
                ax.plot([x + 0.5 for x in xs], [y + 0.5 for y in ys], color=color, linewidth=1, alpha=0.5)
            # Plot current missile position if alive
            if agent.alive:
                ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "o", color=color, markersize=5)
        elif isinstance(agent, TargetAgent):
            # Plot Target agent
            ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "s", color="green", markersize=8)
        elif isinstance(agent, TargetReportingUnit):
            # Plot Target Reporting Unit (TRU)
            ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "^", color="purple", markersize=8)

    # Return the Matplotlib figure wrapped in Solara's component
    return solara.FigureMatplotlib(fig)


@solara.component
def MissileDashboard():
    solara.Title("Naval Missile Simulation")

    # Helper function to check if the simulation should stop
    def simulation_finished():
        # Simulation is finished if:
        # 1. All intended missiles have been launched AND
        # 2. No active missiles remain
        all_missiles_launched = model.value.missile_count >= model.value.num_missiles
        no_active_missiles = not any(isinstance(agent, MissileAgent) and agent.alive for agent in model.value.agents)
        return all_missiles_launched and no_active_missiles

    # Function for automatic stepping in a separate thread
    def auto_step():
        while running.value:
            try:
                if simulation_finished():
                    print("Simulation finished condition met. Stopping auto_step.")
                    running.value = False
                    break
                model.value.step()
                step_count.value += 1
                delay = 2.0 - speed_slider.value * 1.9 # Ranges from 2.0s (slow) to 0.1s (fast)
                time.sleep(delay)
            except Exception as e:
                # Catch any exception during stepping and print it
                print(f"ERROR: Exception caught in auto_step thread: {e}")
                traceback.print_exc() # Print full traceback
                running.value = False # Stop the simulation on error
                break

    # Toggle play/pause functionality
    def toggle_play_pause():
        if running.value:
            print("Pausing simulation.")
            running.value = False
        else:
            print("Starting/Resuming simulation.")
            running.value = True
            # Start auto_step in a daemon thread so it doesn't block program exit
            threading.Thread(target=auto_step, daemon=True).start()

    # Perform a single step of the simulation
    def step():
        if not simulation_finished():
            print("Performing single step.")
            model.value.step()
            step_count.value += 1
        else:
            print("Cannot step, simulation already finished.")

    # Reset the simulation to its initial state
    def reset():
        print("Resetting simulation.")
        # Re-initialize the model with original parameters
        model.value = NavalModel(
            width=WIDTH,
            height=HEIGHT,
            num_missiles=NUM_MISSILES,
            launch_interval=LAUNCH_INTERVAL,
            swarm_mode=SwarmMode.SIMPLE
        )
        step_count.value = 0
        running.value = False

    # Solara UI layout
    with solara.Column():
        solara.Markdown(f"**Step:** {step_count.value}")
        MissileGrid() # Display the simulation grid

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

            # Labels for the slider
            solara.Markdown("Slow", style={"fontSize": "0.8em", "margin": "0"})
            solara.Markdown("Fast", style={"fontSize": "0.8em", "margin": "0"})


@solara.component
def Page():
    # The main page component displays the dashboard
    MissileDashboard()

