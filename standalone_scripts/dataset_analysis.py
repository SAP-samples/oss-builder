import os 
import json
import seaborn as sns
import matplotlib.pyplot as plt
from collections import Counter

this_dir = os.path.dirname(os.path.abspath(__file__))
packages = Counter()
c = 0 

vulnerability_dir = os.path.join(this_dir, '../', 'vuln_stream/' 'data/')
for path in os.listdir(vulnerability_dir):
    with open(os.path.join(vulnerability_dir, path)) as f:
        report = json.load(f)
        packages[report['affected'][0]['package']['name']] += 1
    c += 1


print(c)
# plot a pie chart of the packages
sns.set_theme(style="whitegrid")
plt.pie(packages.values(), labels=packages.keys(), autopct='%1.1f%%', textprops={'fontsize': '9'})
plt.bar()

# plot sorted bar chart
# print(packages)
# sorted_packages = dict(sorted(packages.items(), key=lambda x: x[1], reverse=True))
# sns.set_theme(style="whitegrid")
# sns.barplot(x=list(sorted_packages.keys()), y=list(sorted_packages.values()))

plt.show()
