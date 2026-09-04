import re

with open("generate_tract_map.py", "r") as f:
    code = f.read()

# Replace the single braces in the new injected code with double braces
code = code.replace(
    "if (agg.total_pop > 0 && c_agg.pop > 0) {",
    "if (agg.total_pop > 0 && c_agg.pop > 0) {{"
)
code = code.replace(
    "            } else {",
    "            }} else {{"
)
code = code.replace(
    "                document.getElementById('ms-ratio').innerText = \"0%\";\n            }",
    "                document.getElementById('ms-ratio').innerText = \"0%\";\n            }}"
)

with open("generate_tract_map.py", "w") as f:
    f.write(code)
print("Braces fixed")
