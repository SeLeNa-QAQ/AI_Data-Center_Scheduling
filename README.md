# AI_Data-Center_Scheduling
A simulator comparing baseline and our smart AI data-center scheduling. It weighs electricity price, green supply, PUE (power usage effectiveness), battery state, and task urgency to cut cost and carbon emissions while meeting user-defined deadlines.

We built a 96-step (15-min) day simulation with time-varying price, renewable supply, and PUE, running two strategies on identical tasks: a greedy baseline versus a smart scheduler that scores waiting tasks by price, green availability, spare capacity, and battery state, minus an urgency-scaled waiting penalty. Our twist is that "good" is never collapsed into one number as cost, carbon, and SLA violations stay separate, and the urgency weights themselves are live and adjustable in Streamlit, making the cheaper-vs-greener trade-off an explicit, inspectable policy choice rather than a hidden constant.

How to install: 
1. Download app.py and requirement.txt from github 
2. Open Terminal and enter the following code to download required libraries:
   
python3 -m pip install random

python3 -m pip install matplotlib

python3 -m pip install streamlit

3. Launch the appplication by entering:

streamlit run /Users/app.py

Enter the full file path for the file. If you cannot find the file path for app.py, just drag it into terminal to get the full file path. Then enter your email in the terminal if it asked to do so. The application will be opened in your default browser.
