from pathlib import Path

p = Path('app.py')
text = p.read_text()
marker = 'correct: {c[\'ticket_decision_correct\']}"\n                )'
replacement = ('correct: {c[\'ticket_decision_correct\']}"\n                )\n'
               '                st.write("**Routing Predictions:**")\n'
               '                st.write(\n'
               '                    f"Assignment Group: predicted: {c.get(\'pred_assignment_group\', \'\')} | "\n'
               '                    f"true: {c.get(\'true_assignment_group\', \'\')} | "\n'
               '                    f"correct: {c.get(\'routing_group_correct\', \'\')}"\n'
               '                )\n'
               '                st.write(\n'
               '                    f"Category: predicted: {c.get(\'pred_category\', \'\')} | "\n'
               '                    f"true: {c.get(\'true_category\', \'\')} | "\n'
               '                    f"correct: {c.get(\'routing_category_correct\', \'\')}"\n'
               '                )\n'
               '                st.write(\n'
               '                    f"Subcategory: predicted: {c.get(\'pred_subcategory\', \'\')} | "\n'
               '                    f"true: {c.get(\'true_subcategory\', \'\')} | "\n'
               '                    f"correct: {c.get(\'routing_subcategory_correct\', \'\')}"\n'
               '                )')

if marker not in text:
    raise ValueError('marker not found in app.py')

p.write_text(text.replace(marker, replacement))
print('updated app.py')
