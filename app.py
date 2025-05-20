import solara
import matplotlib.pyplot as plt
import numpy as np
from model import NavalModel
from agents import MissileAgent, TargetAgent
from TargetReportingUnit import TargetReportingUnit

# Reactive state
step_count = solara.reactive(0)
model = solara.reactive(NavalModel())

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

    # Plot all agents
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
    with solara.Column():
        solara.Markdown(f"**Step:** {step_count.value}")
        MissileGrid()

        with solara.Row():
            def step():
                model.value.step()
                step_count.value += 1

            def reset():
                model.value = NavalModel()
                step_count.value = 0

            solara.Button("Step", on_click=step)
            solara.Button("Reset", on_click=reset)

@solara.component
def Page():
    MissileDashboard()