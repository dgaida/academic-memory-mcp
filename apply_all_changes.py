import sys
from pathlib import Path

path = Path('scripts/process_sorted_emails.py')
content = path.read_text(encoding='utf-8')

# 1. Update render_tab1 internal variables and loops to include attachment_checkboxes
old_render_tab1_start = '                    checkboxes = []'
new_render_tab1_start = '                    checkboxes = []\n                    attachment_checkboxes = []'

if old_render_tab1_start in content and new_render_tab1_start not in content:
    content = content.replace(old_render_tab1_start, new_render_tab1_start, 1)

old_box = '''                                        cb = gr.Checkbox(label=f"{mail['lastname']} ({mail['class']})", value=False)
                                        checkboxes.append(cb)
                                        gr.Markdown(f"`{Path(mail['path']).name}`")'''

new_box = '''                                        cb = gr.Checkbox(label=f"{mail['lastname']} ({mail['class']})", value=False)
                                        checkboxes.append(cb)
                                        att_cb = gr.Checkbox(label="Anhang speichern", value=mail.get("save_attachments", False))
                                        attachment_checkboxes.append(att_cb)
                                        gr.Markdown(f"`{Path(mail['path']).name}`")'''

content = content.replace(old_box, new_box)

# 2. Update handle_remove_to_tab2
old_handle = '''                    def handle_remove_to_tab2(t1_mails, t2_mails, *selected_states):
                        actual_selections = []
                        # Map states back to original indices
                        state_idx = 0
                        for idx in inbox_indices:
                            if selected_states[state_idx]:
                                actual_selections.append(idx)
                            state_idx += 1
                        for idx in sent_indices:
                            if selected_states[state_idx]:
                                actual_selections.append(idx)
                            state_idx += 1

                        if not actual_selections:
                            yield t1_mails, t2_mails, "Keine Mails ausgewählt.", gr.update()
                            return

                        yield from remove_to_tab2_logic(t1_mails, t2_mails, actual_selections)'''

new_handle = '''                    def handle_remove_to_tab2(t1_mails, t2_mails, *all_states):
                        """Verarbeitet das Verschieben von Mails von Tab 1 nach Tab 2."""
                        num_main = len(checkboxes)
                        selected_states = all_states[:num_main]
                        attachment_states = all_states[num_main:]

                        actual_selections = []
                        # Map states back to original indices
                        state_idx = 0
                        for idx in inbox_indices:
                            if selected_states[state_idx]:
                                actual_selections.append((idx, attachment_states[state_idx]))
                            state_idx += 1
                        for idx in sent_indices:
                            if selected_states[state_idx]:
                                actual_selections.append((idx, attachment_states[state_idx]))
                            state_idx += 1

                        if not actual_selections:
                            yield t1_mails, t2_mails, "Keine Mails ausgewählt.", gr.update()
                            return

                        yield from remove_to_tab2_logic(t1_mails, t2_mails, actual_selections)'''

content = content.replace(old_handle, new_handle)

# 3. Update click handlers
old_click1 = 'inputs=[tab1_mails, tab2_mails] + checkboxes,'
new_click1 = 'inputs=[tab1_mails, tab2_mails] + checkboxes + attachment_checkboxes,'
content = content.replace(old_click1, new_click1)

old_click2 = '''                    relocate_btn.click(
                        relocate_remaining,
                        inputs=[tab1_mails],
                        outputs=[tab1_mails, tab1_status]
                    )'''

new_click2 = '''                    relocate_btn.click(
                        relocate_remaining,
                        inputs=[tab1_mails] + attachment_checkboxes,
                        outputs=[tab1_mails, tab1_status]
                    )'''

content = content.replace(old_click2, new_click2)

# 4. Update remove_to_tab2_logic
old_logic_def = 'def remove_to_tab2_logic(t1_mails: List[Dict[str, Any]], t2_mails: List[Dict[str, Any]], selected_indices: List[int]) -> Generator:'
new_logic_def = 'def remove_to_tab2_logic(t1_mails: List[Dict[str, Any]], t2_mails: List[Dict[str, Any]], selected_info: List[Tuple[int, bool]]) -> Generator:'
content = content.replace(old_logic_def, new_logic_def)

content = content.replace(
    'selected_indices = sorted(list(set(selected_indices)), reverse=True)',
    'selected_info = sorted(list(set(selected_info)), key=lambda x: x[0], reverse=True)'
)

content = content.replace(
    'for idx in selected_indices:',
    'for idx, att_save in selected_info:'
)

content = content.replace(
    'mail_copy["similarity_info"] = "Suche ähnliche Mails..."',
    'mail_copy["similarity_info"] = "Suche ähnliche Mails..."\n                    mail_copy["save_attachments"] = att_save'
)

# 5. Insert suggested action logic in remove_to_tab2_logic
old_summary_call = '                mail["summary"] = controller.generate_short_summary(mail_path)'
new_summary_call = '''                mail["summary"] = controller.generate_short_summary(mail_path)
                mail["similarity_info"] = controller.get_similarity_info(mail_path, mail["lastname"])
                logger.info(f"Bestimme empfohlene Aktion für {mail['lastname']}...")
                action_idx = controller.get_suggested_action(mail_path, mail, age_months=age_months)
                mail["suggested_action"] = controller.ACTION_OPTIONS[action_idx]'''

# Note: removing the original similarity_info line if it exists
content = content.replace('                mail["similarity_info"] = controller.get_similarity_info(mail_path, mail["lastname"])\n', '')
content = content.replace(old_summary_call, new_summary_call)

# 6. Update relocate_remaining
old_relocate = '''        def relocate_remaining(t1_mails: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
            """Archiviert alle verbleibenden E-Mails in Tab 1."""
            if not t1_mails:
                return [], "Keine Mails zum Verschieben."

            changes = []
            for m in t1_mails:
                change = m.copy()
                change["new_class"] = m["class"]
                changes.append(change)'''

new_relocate = '''        def relocate_remaining(t1_mails: List[Dict[str, Any]], *att_states: Any) -> Tuple[List[Dict[str, Any]], str]:
            """Archiviert alle verbleibenden E-Mails in Tab 1."""
            if not t1_mails:
                return [], "Keine Mails zum Verschieben."

            changes = []
            for i, m in enumerate(t1_mails):
                change = m.copy()
                change["new_class"] = m["class"]
                if i < len(att_states):
                    change["save_attachments"] = att_states[i]
                changes.append(change)'''

content = content.replace(old_relocate, new_relocate)

# 7. Update handle_tab2_process docstring
old_tab2_def = '                    def handle_tab2_process(*args: Any) -> str:'
new_tab2_def = '''                    def handle_tab2_process(*args: Any) -> str:
                        """Verarbeitet die E-Mails in Tab 2."""'''
if old_tab2_def in content and 'Verarbeitet die E-Mails' not in content:
    content = content.replace(old_tab2_def, new_tab2_def)

# 8. Update render_tab2 attachment checkbox
content = content.replace(
    'att_cb = gr.Checkbox(label="Anhang speichern", value=False)',
    'att_cb = gr.Checkbox(label="Anhang speichern", value=mail.get("save_attachments", False))'
)

path.write_text(content, encoding='utf-8')
