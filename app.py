import solara
import matplotlib.pyplot as plt
import numpy as np
import time
import threading

from model import NavalModel
from agents import MissileAgent, TargetAgent
from TargetReportingUnit import TargetReportingUnit

step_count = solara.reactive(0)
model = solara.reactive(NavalModel())
running = solara.reactive(False)
speed_slider = solara.reactive(0.5)  # Mid-speed

grid_width = model.value.grid.width
grid_height = model.value.grid.height


@solara.component
def MissileGrid():
    _ = step_count.value  # Reactive trigger

    fig, ax = plt.subplots(figsize=(10, 2))
    ax.set_xlim(0, grid_width)
    ax.set_ylim(0, grid_height)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

    for agent in model.value.agents:
        if isinstance(agent, MissileAgent):
            color = "red" if agent.exploded else "blue"
            if agent.alive and len(agent.trail) > 1:
                xs, ys = zip(*agent.trail)
                ax.plot([x + 0.5 for x in xs], [y + 0.5 for y in ys], color=color, linewidth=1, alpha=0.5)
            if agent.alive:
                ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "o", color=color)
        elif isinstance(agent, TargetAgent):
            ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "s", color="green")
        elif isinstance(agent, TargetReportingUnit):
            ax.plot(agent.pos[0] + 0.5, agent.pos[1] + 0.5, "^", color="purple")

    return solara.FigureMatplotlib(fig)


@solara.component
def MissileDashboard():
    solara.Title("Naval Missile Simulation")

    def simulation_finished():
        return not any(isinstance(agent, MissileAgent) and agent.alive for agent in model.value.agents)

    def auto_step():
        while running.value:
            if simulation_finished():
                running.value = False
                break
            model.value.step()
            step_count.value += 1
            # Delay: 0 = slow (2.0s), 1 = fast (0.1s)
            delay = 2.0 - speed_slider.value * 1.9
            time.sleep(delay)

    def toggle_play_pause():
        if running.value:
            running.value = False
        else:
            running.value = True
            threading.Thread(target=auto_step, daemon=True).start()

    def step():
        if not simulation_finished():
            model.value.step()
            step_count.value += 1

    def reset():
        model.value = NavalModel()
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
            solara.Markdown("**Speed:**", style={"margin": "0"})  # No margin to misalign

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
