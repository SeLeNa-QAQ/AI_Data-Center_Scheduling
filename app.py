import random
import matplotlib.pyplot as plt
import streamlit as st


# ==========================================
# Page setup
# ==========================================

st.set_page_config(
    page_title="AI Data Center Scheduling Simulation",
    page_icon="⚡",
    layout="wide"
)

st.title("AI Data Center Scheduling Simulation")
st.write(
    "Explore how electricity prices, renewable electricity, computing demand, "
    "and battery settings affect baseline and smart scheduling. "
    "Change the controls in the sidebar to rerun the simulation."
)
st.caption(
    "This is a simplified simulation using generated data, not live electricity-market data. "
    "The default settings reproduce the assumptions in the original code."
)


# ==========================================
# 1. User interface: simulation controls
# ==========================================

with st.sidebar:
    st.header("Simulation controls")
    st.caption(
        "Each slider has a description below it. "
        "Changing a value reruns both simulations."
    )

    st.subheader("Computing demand")

    number_of_tasks = st.slider(
        "Number of tasks",
        min_value=50,
        max_value=500,
        value=200,
        step=25,
        help="More tasks create more computing demand."
    )
    st.caption(
        "How many jobs arrive during the simulated day. "
        "More jobs create more opportunities for scheduling, "
        "but can also increase waiting and missed deadlines."
    )

    demand_multiplier = st.slider(
        "Task workload multiplier",
        min_value=0.5,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="Scales each task's computing requirement. 1.0 keeps the original task sizes."
    )
    st.caption(
        "Multiplies each task's required computing units. "
        "1.0 preserves the original workload sizes; higher values make tasks larger."
    )

    compute_capacity = st.slider(
        "Computing capacity per time step",
        min_value=40,
        max_value=200,
        value=120,
        step=10,
        help="Maximum computing units that can run during one 15-minute step."
    )
    st.caption(
        "Maximum compute units available in each 15-minute interval. "
        "A larger capacity can process more selected tasks in the same interval."
    )

    st.subheader("Electricity and cooling")

    price_multiplier = st.slider(
        "Electricity price multiplier",
        min_value=0.5,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="Scales the original electricity-price curve."
    )
    st.caption(
        "Scales every point of the original daily price curve. "
        "1.0 keeps the original prices; lower values make grid electricity cheaper."
    )

    green_multiplier = st.slider(
        "Renewable electricity multiplier",
        min_value=0.0,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="Scales the original renewable-electricity supply curve."
    )
    st.caption(
        "Scales the original midday renewable supply curve. "
        "0 means no renewable supply; 1.0 preserves the original curve."
    )

    pue_multiplier = st.slider(
        "PUE multiplier",
        min_value=0.91,
        max_value=1.20,
        value=1.0,
        step=0.01,
        help="Scales the original PUE profile. Lower PUE means less overhead energy."
    )
    st.caption(
        "Scales the original cooling and overhead-efficiency profile. "
        "A lower PUE means less total facility energy is needed for the same computing load."
    )

    carbon_intensity = st.slider(
        "Grid carbon intensity",
        min_value=0.0,
        max_value=1.5,
        value=0.8,
        step=0.1,
        help="Carbon emissions per unit of electricity bought from the grid."
    )
    st.caption(
        "Emissions assigned to each unit of grid electricity. "
        "This changes reported carbon emissions, but does not directly change task-selection scores."
    )

    st.subheader("Battery")

    battery_capacity = st.slider(
        "Battery capacity",
        min_value=0,
        max_value=600,
        value=300,
        step=25,
        help="Maximum energy stored in the battery."
    )
    st.caption(
        "Maximum stored energy. The battery begins the day empty "
        "and can store surplus renewable electricity when available."
    )

    battery_rate = st.slider(
        "Battery charging/discharging rate",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        help="Maximum energy that can be charged or discharged in one time step."
    )
    st.caption(
        "Limits how quickly the battery can charge or discharge in one "
        "15-minute interval. A rate of 0 disables battery movement."
    )

    st.subheader("Smart scheduling")

    score_threshold = st.slider(
        "Scheduling score threshold",
        min_value=0.0,
        max_value=1.2,
        value=0.6,
        step=0.05,
        help="A waiting task can be selected before its deadline approaches when its score is above this value."
    )
    st.caption(
        "A task is selected early only when its score is above this threshold. "
        "Tasks close to their deadlines still follow the original automatic-selection rule."
    )

    with st.expander("Advanced: scoring weights by urgency group", expanded=False):
        st.write(
            "Adjust the importance of price, renewable electricity, available capacity, "
            "battery availability, and waiting time for each urgency group. "
            "Each group's weights are normalized to sum to 1. "
            "The default values match the original code."
        )

        default_weights = {
            "G0": {
                "w_price": 0.0, "w_green": 0.0,
                "w_cap": 0.1, "w_batt": 0.0, "w_wait": 0.9
            },
            "G1": {
                "w_price": 0.2, "w_green": 0.0,
                "w_cap": 0.2, "w_batt": 0.1, "w_wait": 0.5
            },
            "G2": {
                "w_price": 0.3, "w_green": 0.3,
                "w_cap": 0.1, "w_batt": 0.1, "w_wait": 0.2
            },
            "G3": {
                "w_price": 0.4, "w_green": 0.4,
                "w_cap": 0.1, "w_batt": 0.1, "w_wait": 0.0
            }
        }

        weight_labels = {
            "w_price": "Electricity price",
            "w_green": "Renewable electricity",
            "w_cap": "Available capacity",
            "w_batt": "Battery availability",
            "w_wait": "Waiting time"
        }

        weight_descriptions = {
            "w_price": (
                "Higher values give the price score more influence "
                "in this group's task score."
            ),
            "w_green": (
                "Higher values give the renewable-electricity score more influence."
            ),
            "w_cap": (
                "Higher values give the available-capacity score more influence."
            ),
            "w_batt": (
                "Higher values give the battery-availability score more influence."
            ),
            "w_wait": (
                "Higher values strengthen the waiting-time term, "
                "which is subtracted in the existing formula."
            )
        }

        input_weights = {}

        for group in ["G0", "G1", "G2", "G3"]:
            st.markdown(f"**{group} urgency group**")
            input_weights[group] = {}

            for weight_name, label in weight_labels.items():
                input_weights[group][weight_name] = st.slider(
                    f"{group}: {label}",
                    min_value=0.0,
                    max_value=1.0,
                    value=default_weights[group][weight_name],
                    step=0.1,
                    key=f"{group}_{weight_name}"
                )
                st.caption(weight_descriptions[weight_name])


# ==========================================
# 2. Creating the simulation data
# ==========================================

STEPS = 96  # 24 hours, 15 minutes per step


def create_environment(price_scale, green_scale, pue_scale):
    """Create the original daily curves using the selected input multipliers."""

    price_list = []
    green_list = []
    pue_list = []

    for i in range(STEPS):

        # 1. Electricity price
        if i < 24 or i > 80:
            price_list.append(0.2 * price_scale)
        elif 40 < i < 72:
            price_list.append(1.0 * price_scale)
        else:
            price_list.append(0.5 * price_scale)

        # 2. Renewable electricity
        if i < 32 or i > 64:
            green_list.append(0)
        elif i <= 48:
            value = (i - 32) * (100 / 16)
            green_list.append(value * green_scale)
        else:
            value = 100 - (i - 48) * (100 / 16)
            green_list.append(value * green_scale)

        # 3. PUE
        if i < 24 or i > 80:
            pue_list.append(1.1 * pue_scale)
        else:
            pue_list.append(1.4 * pue_scale)

    return {
        "price": price_list,
        "green": green_list,
        "PUE": pue_list
    }


env_data = create_environment(
    price_multiplier,
    green_multiplier,
    pue_multiplier
)


# ==========================================
# 3. Creating the task pool
# ==========================================

def create_task_pool(task_count, workload_scale):
    """Generate the same tasks for both strategies."""

    rng = random.Random(42)
    tasks = []

    for i in range(task_count):
        arrival = rng.randint(0, 90)
        urgency = rng.choice(["G0", "G1", "G2", "G3"])
        need = int(round(rng.randint(10, 40) * workload_scale))
        need = max(1, need)

        if urgency == "G0":
            deadline = arrival + 1
        elif urgency == "G1":
            deadline = arrival + 4
        elif urgency == "G2":
            deadline = arrival + 12
        else:
            deadline = arrival + 24

        task = {
            "id": i,
            "arrival": arrival,
            "need": need,
            "urgency": urgency,
            "deadline": deadline
        }

        tasks.append(task)

    return tasks


task_pool = create_task_pool(number_of_tasks, demand_multiplier)


# ==========================================
# 4. Scoring weights
# ==========================================

def get_normalized_weights(raw_weights, fallback_weights):
    """Normalize weights while keeping the original defaults."""

    normalized = {}

    for group in ["G0", "G1", "G2", "G3"]:
        total = sum(raw_weights[group].values())

        if total == 0:
            normalized[group] = fallback_weights[group].copy()
        else:
            normalized[group] = {}

            for name, value in raw_weights[group].items():
                normalized[group][name] = value / total

    return normalized


weighted_dict = get_normalized_weights(input_weights, default_weights)


# ==========================================
# 5. Running the simulation
# ==========================================

def run_simulation(
    smart,
    environment,
    tasks,
    cap_max,
    battery_cap,
    battery_rate_limit,
    threshold,
    grid_carbon_intensity,
    group_weights
):
    """Run either the baseline or smart scheduling strategy."""

    battery_soc = 0
    total_cost = 0
    total_carbon = 0
    sla_violations = 0
    waiting_queue = []

    log = {
        "compute": [],
        "battery": [],
        "grid_used": []
    }

    for t in range(STEPS):
        cap_remain = cap_max

        # 1. Receive new tasks.
        for task in tasks:
            if task["arrival"] == t:
                waiting_queue.append(task)

        # 2. Select tasks and calculate their priority scores.
        current_tasks = []
        priority_scores = {}

        for task in waiting_queue:

            # Baseline: try to run every waiting task.
            if not smart:
                current_tasks.append(task)

            # Tasks near their deadlines follow the original selection rule.
            elif t >= task["deadline"] - 1:
                current_tasks.append(task)
                priority_scores[task["id"]] = float("inf")

            else:
                # Normalize the indicators using the original formulas.
                p_score = 1 - (
                    environment["price"][t] * environment["PUE"][t] - 0.2
                ) / 1.5

                g_score = environment["green"][t] / 100

                k_score = cap_remain / cap_max

                if battery_soc > 50 and environment["price"][t] > 0.6:
                    b_score = 1
                else:
                    b_score = 0

                w_score = (
                    (t - task["arrival"])
                    / max(1, task["deadline"] - task["arrival"])
                )

                # Use the input weights for this task's urgency group.
                w = group_weights[task["urgency"]]

                # Original comprehensive scoring formula: unchanged.
                score = (
                    p_score * w["w_price"]
                    + g_score * w["w_green"]
                    + k_score * w["w_cap"]
                    + b_score * w["w_batt"]
                    - w_score * w["w_wait"]
                )

                # Select the task if its score passes the threshold.
                if score > threshold:
                    current_tasks.append(task)
                    priority_scores[task["id"]] = score

        # Rank selected smart-scheduling tasks before allocating capacity.
        # Higher score comes first; earlier deadline breaks ties.
        # The baseline remains in its original queue order.
        if smart:
            current_tasks.sort(
                key=lambda task: (
                    priority_scores[task["id"]],
                    -task["deadline"]
                ),
                reverse=True
            )

        # 3. Run selected tasks subject to available computing capacity.
        for task in current_tasks:

            if t > task["deadline"]:
                sla_violations += 1
                waiting_queue.remove(task)
                continue

            if cap_remain >= task["need"]:
                cap_remain -= task["need"]
                waiting_queue.remove(task)

        # 4. Calculate electricity demand.
        compute_used = cap_max - cap_remain

        power_demand = (
            compute_used * environment["PUE"][t]
        )

        green_available = environment["green"][t]

        if green_available >= power_demand:

            # Green electricity covers all demand.
            grid_used = 0
            surplus_green = green_available - power_demand

            charge = min(
                surplus_green,
                battery_rate_limit,
                battery_cap - battery_soc
            )

            battery_soc += charge

        else:

            # Use green electricity first.
            shortage = power_demand - green_available

            # Discharge the battery when electricity is expensive.
            if environment["price"][t] > 0.6 and battery_soc > 0:

                discharge = min(
                    shortage,
                    battery_rate_limit,
                    battery_soc
                )

                battery_soc -= discharge
                shortage -= discharge

            # Buy the remaining electricity from the grid.
            grid_used = shortage

            total_cost += grid_used * environment["price"][t]
            total_carbon += grid_used * grid_carbon_intensity

        # 5. Save data for plotting.
        log["compute"].append(compute_used)
        log["battery"].append(battery_soc)
        log["grid_used"].append(grid_used)

    # Count unfinished tasks whose deadlines fall within this day.
    for task in waiting_queue:
        if task["deadline"] < STEPS:
            sla_violations += 1

    return total_cost, total_carbon, sla_violations, log


# ==========================================
# 6. Compare baseline and smart scheduling
# ==========================================

with st.spinner("Running both scheduling simulations..."):

    base_cost, base_carbon, base_sla, base_hist = run_simulation(
        False,
        env_data,
        task_pool,
        compute_capacity,
        battery_capacity,
        battery_rate,
        score_threshold,
        carbon_intensity,
        weighted_dict
    )

    smart_cost, smart_carbon, smart_sla, smart_hist = run_simulation(
        True,
        env_data,
        task_pool,
        compute_capacity,
        battery_capacity,
        battery_rate,
        score_threshold,
        carbon_intensity,
        weighted_dict
    )


def percentage_reduction(original, new_value):
    if original == 0:
        return None

    return (original - new_value) / original * 100


cost_saving = percentage_reduction(base_cost, smart_cost)
carbon_reduction = percentage_reduction(base_carbon, smart_carbon)


# ==========================================
# 7. Display numerical results
# ==========================================

st.header("Simulation results")
st.write(
    "Both strategies receive the same generated tasks "
    "and environment settings."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Baseline electricity cost", f"{base_cost:,.1f}")

with col2:
    st.metric("Smart electricity cost", f"{smart_cost:,.1f}")

with col3:
    if cost_saving is None:
        st.metric("Electricity cost reduction", "N/A")
    else:
        st.metric(
            "Electricity cost reduction",
            f"{cost_saving:.1f}%"
        )


col4, col5, col6 = st.columns(3)

with col4:
    st.metric("Baseline carbon emissions", f"{base_carbon:,.1f}")

with col5:
    st.metric("Smart carbon emissions", f"{smart_carbon:,.1f}")

with col6:
    if carbon_reduction is None:
        st.metric("Carbon emissions reduction", "N/A")
    else:
        st.metric(
            "Carbon emissions reduction",
            f"{carbon_reduction:.1f}%"
        )


col7, col8 = st.columns(2)

with col7:
    st.metric("Baseline SLA violations", str(base_sla))

with col8:
    st.metric("Smart SLA violations", str(smart_sla))


if smart_sla > base_sla:
    st.warning(
        "Smart scheduling has more SLA violations under these settings. "
        "Try a lower score threshold or a higher computing capacity."
    )


# ==========================================
# 8. Plot results in the Streamlit webpage
# ==========================================

st.header("Daily operating patterns")

time_steps = list(range(STEPS))
time_ticks = list(range(0, STEPS, 8))
time_labels = [f"{step // 4:02d}:00" for step in time_ticks]


# Figure 1: price, renewable supply, and computing load.
fig1, axes1 = plt.subplots(
    3, 1,
    figsize=(12, 9),
    sharex=True
)

axes1[0].plot(
    time_steps,
    env_data["price"],
    color="red",
    linewidth=2
)
axes1[0].set_ylabel("Price")
axes1[0].set_title("Electricity price")
axes1[0].grid(True, alpha=0.3)

axes1[1].plot(
    time_steps,
    env_data["green"],
    color="green",
    linewidth=2
)
axes1[1].set_ylabel("Energy units")
axes1[1].set_title("Renewable electricity available")
axes1[1].grid(True, alpha=0.3)

axes1[2].plot(
    time_steps,
    base_hist["compute"],
    label="Baseline computing load",
    color="gray",
    alpha=0.85
)
axes1[2].plot(
    time_steps,
    smart_hist["compute"],
    label="Smart computing load",
    color="blue",
    linewidth=2
)
axes1[2].set_ylabel("Compute units")
axes1[2].set_title("Computing load comparison")
axes1[2].legend(loc="upper right")
axes1[2].grid(True, alpha=0.3)

for ax in axes1:
    ax.set_xticks(time_ticks)
    ax.set_xticklabels(time_labels)

axes1[2].set_xlabel("Time of day (each step is 15 minutes)")
fig1.tight_layout()

# Important: do not add width="stretch" here.
st.pyplot(fig1)
plt.close(fig1)


# Figure 2: battery level and grid electricity.
fig2, axes2 = plt.subplots(
    2, 1,
    figsize=(12, 7),
    sharex=True
)

axes2[0].plot(
    time_steps,
    base_hist["battery"],
    label="Baseline battery level",
    color="gray"
)
axes2[0].plot(
    time_steps,
    smart_hist["battery"],
    label="Smart battery level",
    color="purple",
    linewidth=2
)
axes2[0].set_ylabel("Stored energy")
axes2[0].set_title("Battery level")
axes2[0].legend(loc="upper right")
axes2[0].grid(True, alpha=0.3)

axes2[1].plot(
    time_steps,
    base_hist["grid_used"],
    label="Baseline grid electricity",
    color="gray",
    alpha=0.9
)
axes2[1].plot(
    time_steps,
    smart_hist["grid_used"],
    label="Smart grid electricity",
    color="orange",
    linewidth=2
)
axes2[1].set_ylabel("Energy units")
axes2[1].set_title("Electricity purchased from the grid")
axes2[1].legend(loc="upper right")
axes2[1].grid(True, alpha=0.3)

for ax in axes2:
    ax.set_xticks(time_ticks)
    ax.set_xticklabels(time_labels)

axes2[1].set_xlabel("Time of day (each step is 15 minutes)")
fig2.tight_layout()

# Important: do not add width="stretch" here either.
st.pyplot(fig2)
plt.close(fig2)


# ==========================================
# 9. Methodology summary shown on the webpage
# ==========================================

with st.expander("Model methodology and assumptions", expanded=False):

    st.markdown("""
    **Time resolution:** 96 steps per day, with 15 minutes per step.

    **Baseline strategy:** attempts to run every waiting task, subject to available computing capacity.

    **Smart strategy:** selects tasks close to their deadlines, or selects earlier tasks when their weighted score is above the chosen threshold.

    **Scoring formula:**
    """)

    st.latex(
        r"S = w_{price}P + w_{green}G + w_{cap}K + w_{batt}B - w_{wait}W"
    )

    st.markdown("""
    The score components, urgency-specific weights, deadline rule, battery
    charging and discharging rules, and cost/carbon calculations follow the
    original code. The sidebar allows users to change simulation inputs and
    scoring weights without replacing the scoring equation.

    **Cost:** grid electricity used multiplied by the electricity price.

    **Carbon emissions:** grid electricity used multiplied by the chosen grid carbon intensity.

    The tasks and daily curves are generated from stated assumptions, so the
    results are illustrative and should not be presented as measured real-world performance.
    """)
    
 # ==========================================
# 10. Visible task priority rankings
# ==========================================

st.header("Task Priority Rankings")

st.write(
    "View how the smart scheduler ranks tasks within each urgency group. "
    "The ranking uses your current simulation settings and scoring weights."
)

st.caption(
    "This is a priority-score preview for tasks that have arrived by the "
    "selected time step, assuming they are still waiting. It does not track "
    "which tasks have already finished in the simulation."
)

# Let the user choose when to evaluate task priorities.
rank_time = st.slider(
    "Evaluate priorities at time step",
    min_value=0,
    max_value=STEPS - 1,
    value=48,
    step=1,
    help="Each step represents 15 minutes. Step 48 corresponds to 12:00 noon."
)

rank_hour = (rank_time * 15) // 60
rank_minute = (rank_time * 15) % 60

st.caption(
    f"Evaluation time: {rank_hour:02d}:{rank_minute:02d}"
)

# Estimate the battery state at the start of this time step.
if rank_time == 0:
    rank_battery_soc = 0
else:
    rank_battery_soc = smart_hist["battery"][rank_time - 1]

# Create a separate list for each urgency group.
ranked_groups = {
    "G0": [],
    "G1": [],
    "G2": [],
    "G3": []
}

# Calculate each arrived task's score using the existing formula.
for task in task_pool:

    # Tasks that have not arrived are not ranked yet.
    if task["arrival"] > rank_time:
        continue

    # Use the same deadline override as the smart scheduler.
    if rank_time >= task["deadline"] - 1:
        score = float("inf")

        if rank_time > task["deadline"]:
            status = "Deadline override — overdue"
        else:
            status = "Deadline override"

    else:
        # Normalize indicators using the original formulas.
        p_score = 1 - (
            env_data["price"][rank_time]
            * env_data["PUE"][rank_time] - 0.2
        ) / 1.5

        g_score = env_data["green"][rank_time] / 100

        # In the original selection loop, capacity has not yet
        # been allocated when task scores are calculated.
        k_score = compute_capacity / compute_capacity

        if (
            rank_battery_soc > 50
            and env_data["price"][rank_time] > 0.6
        ):
            b_score = 1
        else:
            b_score = 0

        w_score = (
            (rank_time - task["arrival"])
            / max(1, task["deadline"] - task["arrival"])
        )

        # Use this group's current adjustable weights.
        w = weighted_dict[task["urgency"]]

        # Original comprehensive scoring formula: unchanged.
        score = (
            p_score * w["w_price"]
            + g_score * w["w_green"]
            + k_score * w["w_cap"]
            + b_score * w["w_batt"]
            - w_score * w["w_wait"]
        )

        if score > score_threshold:
            status = "Selected — score above threshold"
        else:
            status = "Not selected — below threshold"

    ranked_groups[task["urgency"]].append({
        "task_id": task["id"] + 1,
        "score": score,
        "arrival": task["arrival"],
        "deadline": task["deadline"],
        "need": task["need"],
        "status": status
    })


# Display a separate ranking table for each group.
tabs = st.tabs([
    "G0 — Highest urgency",
    "G1 — High urgency",
    "G2 — Medium urgency",
    "G3 — Lowest urgency"
])

for group, tab in zip(["G0", "G1", "G2", "G3"], tabs):

    with tab:
        tasks_in_group = ranked_groups[group]

        st.subheader(f"{group} Priority Ranking")

        st.caption(
            "Weights used — "
            f"Price: {weighted_dict[group]['w_price']:.2f} | "
            f"Green: {weighted_dict[group]['w_green']:.2f} | "
            f"Capacity: {weighted_dict[group]['w_cap']:.2f} | "
            f"Battery: {weighted_dict[group]['w_batt']:.2f} | "
            f"Waiting: {weighted_dict[group]['w_wait']:.2f}"
        )

        if not tasks_in_group:
            st.info(
                "No tasks from this group have arrived by the selected time."
            )
            continue

        # Rank by score, with earlier deadlines breaking ties.
        tasks_in_group.sort(
            key=lambda task: (
                task["score"],
                -task["deadline"]
            ),
            reverse=True
        )

        display_rows = []

        for rank, task in enumerate(tasks_in_group, start=1):

            if task["score"] == float("inf"):
                score_text = "Deadline priority"
            else:
                score_text = f"{task['score']:.3f}"

            display_rows.append({
                "Rank": rank,
                "Task": f"Task {task['task_id']:03d}",
                "Priority Score": score_text,
                "Arrival Step": task["arrival"],
                "Deadline Step": task["deadline"],
                "Compute Need": task["need"],
                "Selection Status": task["status"]
            })

        st.write(
            f"**{len(tasks_in_group)} tasks** from this group "
            "have arrived by the selected time."
        )

        # Interactive, searchable table.
        st.dataframe(
            display_rows,
            use_container_width=True
        )