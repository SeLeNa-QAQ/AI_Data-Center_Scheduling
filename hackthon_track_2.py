import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import random

#Creating the simulation data
STEPS = 96 #a day is divided into 96 steps, 15 minutes each
#1.electricity price
price_list = []
for i in range(STEPS):
    if i < 24 or i > 80:
        price_list.append(0.2) 
    elif 40 < i < 72:
        price_list.append(1.0)
    else:
        price_list.append(0.5)

#2. green electricity
green_list = []
for i in range(STEPS):
    if i < 32 or i > 64: #little sunlight in morning/evening
        green_list.append(0)
    elif i <= 48:
        value = (i - 32) * (100 / 16) #gradually increasing sunlight from morning to noon
        green_list.append(value)
    else: #gradually decreasing sunlight from noon to evening
        value = 100 - (i - 48) * (100 / 16)
        green_list.append(value)

#3. PUE efficiency
pue_list = []
for i in range(STEPS):
    if i < 24 or i > 80:
        pue_list.append(1.1) #cooler temperature
    else:
        pue_list.append(1.4) # warmer temperature


env_data = {'price': price_list, 'green': green_list, 'PUE': pue_list}



# 2. Creating the task pool
task_pool = []
for i in range(200):
    arrival = random.randint(0, 90) #only 0-90 because we are not taking account of tasks that will be performed after this day
    urgency = random.choice(['G0', 'G1', 'G2', 'G3'])
    need = random.randint(10, 40) #needed capacity to run the task
    
    if urgency == 'G0':
        deadline = arrival + 1
    elif urgency == 'G1':
        deadline = arrival + 4
    elif urgency == 'G2':
        deadline = arrival + 12
    else:
        deadline = arrival + 24
    
    task_pool.append({
        'id': str(i), 'arrival': arrival, 'need': need, 'urgency': urgency, 'deadline': deadline
    })



# Weighted Dictionary
weighted_dict = {
    'G0': {'w_price': 0.0, 'w_green': 0.0, 'w_cap': 0.1, 'w_batt': 0.0, 'w_wait': 0.9},
    'G1': {'w_price': 0.2, 'w_green': 0.0, 'w_cap': 0.2, 'w_batt': 0.1, 'w_wait': 0.5},
    'G2': {'w_price': 0.3, 'w_green': 0.3, 'w_cap': 0.1, 'w_batt': 0.1, 'w_wait': 0.2},
    'G3': {'w_price': 0.4, 'w_green': 0.4, 'w_cap': 0.1, 'w_batt': 0.1, 'w_wait': 0.0}
}


##############################3


def run_simulation(flag):
    cap_max = 120.0
    battery_cap = 300.0
    battery_soc = 0.0
    battery_rate = 50.0 #maximum charging rate (MW)
    
    total_cost = 0.0
    total_carbon = 0.0
    sla_violations = 0
    waiting_queue = []
    
    # 记录画图数据
    log = {'compute': [], 'battery': [], 'grid_used': []} #grid used: amount of electricity purchased (
    
    for t in range(STEPS):
        cap_remain = cap_max
        grid_used = 0
        
        # 1. recieving new tasks
        for task in task_pool:
            if task['arrival'] == t:
                waiting_queue.append(task)
            
        # 2. processing tasks in the queue
        current_tasks = []
        for task in list(waiting_queue):
            if flag==False: #control group (not using our method)
                current_tasks.append(task)
            elif t >= task['deadline'] - 1: #if task at deadline/overtime, run immediately
                current_tasks.append(task)
            else: #experiment group (using the weighted equation)
                p_score = 1- (env_data['price'][t] * env_data['PUE'][t] - 0.2) / 1.5
                g_score = env_data['green'][t] / 100
                k_score = cap_remain / cap_max
                if battery_soc > 50 and env_data['price'][t] >0.6:
                    b_score=1
                else:
                    b_score=0
                w_score = (t - task['arrival']) / max(1, (task['deadline'] - task['arrival']))
                
                w = weighted_dict[task['urgency']]
                S = (p_score * w['w_price'] + g_score * w['w_green'] + k_score * w['w_cap'] + b_score * w['w_batt'] - w_score * w['w_wait'])
                
                # 阈值 0.6：得分超过 0.6 就跑 (可以调整！)
                if S > 0.6:
                    current_tasks.append(task)

        
        # 3. running the tasks and calculating the results
        for task in current_tasks:
            if t > task['deadline']: #if the task is overdue, we give it up...:(
                sla_violations += 1
                waiting_queue.remove(task)
                continue 
    
            if cap_remain >= task['need']:
                cap_remain -= task['need']
                waiting_queue.remove(task)

        # 4. calculating the electricity use
        compute_used = cap_max - cap_remain
        power_demand = compute_used * env_data['PUE'][t] 
        
        green_available = env_data['green'][t]
        if  green_available >= power_demand: #green electricity is enough to cover all usage
            grid_used = 0
            surplus_green = green_available - power_demand
            charge = min(surplus_green, battery_rate, battery_cap - battery_soc)
            battery_soc += charge
        else: #not enough green electricity
            shortage = power_demand - green_available
            if env_data['price'][t] > 0.6 and battery_soc > 0: #if the electricity price is expensive + battery is charged, use electricity from the battery
                discharge = min(shortage, battery_rate, battery_soc)
                battery_soc -= discharge
                shortage -= discharge
            
            grid_used = shortage #the rest would be covered up by purchased electricity
            total_cost += grid_used * env_data['price'][t]

            total_carbon += grid_used * 0.8 #rough estimation of carbon emission
            
        log['compute'].append(compute_used)
        log['battery'].append(battery_soc)
        log['grid_used'].append(grid_used)

    return total_cost, total_carbon, sla_violations, log

############################


#Running the simulation
#Control group
base_cost, base_carbon, base_sla, _ = run_simulation(flag=False)

#Experiment group
smart_cost, smart_carbon, smart_sla, smart_hist = run_simulation(flag=True)


print("Results:")
print("1. The electricity fee: \nBaseline ￥" + str(base_cost) + "\nSmart scheduling ￥" + str(smart_cost) + " (saved " + str(round((1-smart_cost/base_cost)*100, 1)) + "%)")
print("2. Carbon emission: \nBaseline " + str(base_carbon) + " tons\nSmart scheduling " + str(smart_carbon) + " tons (reduced " + str(round((1-smart_carbon/base_carbon)*100, 1)) + "%)")
print("3. SLA violations: \nBaseline " + str(base_sla) + " tasks\nSmart scheduling " + str(smart_sla) + " tasks")

######################################

#Graph result
plt.subplot(2, 1, 1) 

#Graph 1. environment data
plt.plot(env_data['price'], color='red', linestyle='--', label='Electricity Price (Yuan)')
plt.plot(env_data['green'], color='green', alpha=0.3, label='Green Energy (MW)')
plt.plot(smart_hist['compute'], color='blue', linewidth=2, label='Compute Load (MW)')
plt.ylabel('Power / Price')
plt.title('Smart Data Center Scheduling Simulation (24h)')
plt.legend(loc='upper left')
plt.grid(True, alpha=0.3)

#Graph 2.system data & simulation results
plt.subplot(2, 1, 2) 
plt.plot(smart_hist['battery'], color='purple', linewidth=2, label='Battery SOC (MWh)')
plt.bar(range(STEPS), smart_hist['grid_used'], color='orange', alpha=0.5, label='Grid Power Used (MW)')
plt.xlabel('Time Steps (15 min each)')
plt.ylabel('Battery / Grid Power')
plt.legend(loc='upper left')
plt.grid(True, alpha=0.3)

plt.show()

