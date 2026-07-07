import sys
from pathlib import Path

path = Path('scripts/process_sorted_emails.py')
content = path.read_text(encoding='utf-8')

# Fix handle_remove_to_tab2
old_handle = '                    def handle_remove_to_tab2(t1_mails, t2_mails, *all_states):'
new_handle = '''                    def handle_remove_to_tab2(t1_mails, t2_mails, *all_states):
                        """Verarbeitet das Verschieben von Mails von Tab 1 nach Tab 2.

                        Args:
                            t1_mails: Liste der Mails in Tab 1.
                            t2_mails: Liste der Mails in Tab 2.
                            *all_states: Checkbox-Zustände.
                        \"\"\"'''
if old_handle in content and 'Verarbeitet das Verschieben' not in content:
    content = content.replace(old_handle, new_handle)

# Fix handle_tab2_process
old_tab2 = '                    def handle_tab2_process(*args: Any) -> str:'
new_tab2 = '''                    def handle_tab2_process(*args: Any) -> str:
                        """Verarbeitet die Mails in Tab 2.

                        Args:
                            *args: Dynamische Argumente (Klasse, Aktion, Anhang).

                        Returns:
                            str: Statusmeldung.
                        \"\"\"'''
if old_tab2 in content and 'Verarbeitet die Mails in Tab 2' not in content:
    content = content.replace(old_tab2, new_tab2)

path.write_text(content, encoding='utf-8')
