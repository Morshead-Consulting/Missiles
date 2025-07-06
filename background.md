**Observation Space**

Meaning: The observation space defines what information the RL agent receives about its current environment (the simulation state) at each step. It's the agent's "senses" or "perception" of the world. The agent uses this information to decide what action to take next.

In **MissileRLAgent.py**: the MissileRLAgent's get_observation() method explicitly defines its observation space.

The **MissileRLAgent** observes its normalized X and Y position, its normalized displacement (dx, dy) from the estimated target, its normalized remaining fuel, and its missile type.

The observation is a numpy array of 6 floating-point values. 

A well-designed observation space provides enough relevant information for the agent to learn optimal behavior, but not so much irrelevant information that it becomes difficult to learn. If crucial information is missing, the agent might not be able to achieve its goal. If too much noisy or redundant information is present, learning can be slow or unstable.

**Episode**

An episode in RL refers to a single complete "run" or trial of the environment, from its initial state until a terminal state is reached. A terminal state is when the task is either successfully completed, failed, or a predefined time limit is reached.

An episode for the MissileRLAgent starts with a new missile being spawned at an initial position, with initial fuel and a target estimate.

The idea is that an episode ends when the missile either:
* Hits the target (self.exploded = True).
* Runs out of fuel (self.fuel <= 0).
* A maximum number of simulation steps is reached (a timeout).

RL agents learn from experience gained across many **episodes**. Each episode provides a new set of data points (observations, actions, rewards) that the agent uses to update its policy. Running many episodes is crucial for the agent to explore different scenarios and learn robust behavior.

**Reward**

The reward is a scalar numerical feedback signal that the agent receives from the environment after performing an action. It tells the agent how good or bad its last action was in achieving its overall goal. The agent's objective is to maximize the cumulative reward over an entire episode.
MissileRLAgent's get_reward() method defines the reward function.

The missile gets a large positive reward (+100.0) for hitting the target.
The missile receives a large negative reward (-50.0) if it runs out of fuel or becomes inactive without hitting the target.

For every step the missile remains active but hasn't hit the target, it gets a reward based on how much closer it got to the target (improvement * 10) minus a small penalty (-1). This encourages the missile to move towards the target efficiently.

The **reward** function is arguably the most critical component in RL. It directly shapes the agent's learning. A well-designed reward function guides the agent towards the desired behavior. A poorly designed one can lead to unintended behaviors or prevent the agent from learning at all. For example, if the negative step penalty was too high, the missile might learn to crash quickly to avoid penalties, rather than pursuing the target.

**Hyperparameters**

Hyperparameters are parameters that are set before the training process begins, as opposed to model parameters (like weights and biases in a neural network) that are learned during training. They control the learning algorithm's behavior and performance.

In neural network training (used for the RL agents in this simulation), the batch_size determines the number of samples (experiences from the environment, like observation-action-reward tuples) that are processed together in one forward/backward pass to update the network's weights.

Too small a batch_size, can lead to noisy gradient updates, making training unstable or slower to converge.

Too large a batch_size, can lead to slower updates per batch, potentially getting stuck in local optima, and requires more memory. A larger batch might also generalize less well if it doesn't represent the diversity of experiences.

The choice of hyperparameters significantly impacts the training speed, stability, and ultimately, the performance of your RL agent.  Finding the optimal set of hyperparameters often involves a process of trial and error, systematic searching (like grid search or random search), or more advanced techniques (like Bayesian optimization). This process is known as "hyperparameter tuning."  Optimal hyperparameters are highly dependent on the specific environment, task, and RL algorithm being used. What works well for one problem might not for another.

**Epochs**

In the context of RL algorithms like PPO (Proximal Policy Optimization), **epochs** refers to how many times the collected batch of experience is iterated over to perform policy updates before gathering new experiences from the environment.

If there are too few epochs, the policy might not be updated enough from the collected data, leading to slow learning.

If there are too many epochs, this can lead to the policy overfitting to the current batch of data, potentially making it perform poorly on new, unseen experiences (especially if the environment is non-stationary) or cause "policy collapse" where it moves too far from the previous policy.

**Learning rate**

The **learning rate** determines the size of the steps taken when adjusting the neural network's weights during the optimization process (gradient descent). It controls how quickly the model adapts to new information.

Too high a **learning rate**: the optimization might overshoot the optimal weights, leading to oscillations, divergence, or unstable training.

Too low a **learning rate**: training might be very slow, taking a long time to converge to an optimal solution. It might also get stuck in shallow local optima.
