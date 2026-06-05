import re
from pathlib import Path

path = Path("mcp_university/classifier/engine.py")
content = path.read_text()

# Update __init__ docstring
content = content.replace("method: Klassifizierungsmethode ('randomforest', 'xgboost').", "method: Klassifizierungsmethode ('randomforest', 'xgboost', 'transformer').")

# Update __init__ logic
old_init_block = """        if method == "randomforest":
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        elif method == "xgboost":
            from xgboost import XGBClassifier
            self.classifier = XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
        else:
            raise ValueError(f"Ungültige Klassifizierungsmethode: {method}")"""

new_init_block = """        if method == "randomforest":
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        elif method == "xgboost":
            from xgboost import XGBClassifier
            self.classifier = XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
        elif method == "transformer":
            self.classifier = None  # Wird im Training oder beim Laden initialisiert
            self.tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
        else:
            raise ValueError(f"Ungültige Klassifizierungsmethode: {method}")"""

content = content.replace(old_init_block, new_init_block)

# Add _format_transformer_input method
format_method = """
    def _format_transformer_input(self, file_path: Path) -> str:
        \"\"\"Formatiert die E-Mail-Komponenten für den Transformer-Input.\"\"\"
        try:
            import extract_msg
            with extract_msg.openMsg(str(file_path)) as msg:
                subject = msg.subject or '(No Subject)'
                body = msg.body or ''
                attachment_names = []
                for att in msg.attachments:
                    name = None
                    if hasattr(att, "getFilename"):
                        try:
                            name = att.getFilename()
                        except Exception: pass
                    if not name:
                        name = getattr(att, "name", None) or getattr(att, "longFilename", None)
                    if name:
                        attachment_names.append(name)

                attachments_str = ", ".join(attachment_names) if attachment_names else "None"
                formatted = f"SUBJECT: {subject} | ATTACHMENTS: {attachments_str} [SEP] {body}"
                return anonymize_th_koeln_names(formatted)
        except Exception as e:
            logger.warning(f"Error formatting transformer input for {file_path}: {e}")
            text = self._extract_text(file_path)
            return anonymize_th_koeln_names(text) if text else ""
"""

# Find place to insert (before preprocess_data)
content = content.replace("    def preprocess_data(self, root_dir: Union[str, Path]) -> Tuple[List[str], List[str]]:", format_method + "\n    def preprocess_data(self, root_dir: Union[str, Path]) -> Tuple[List[str], List[str]]:")

# Update preprocess_data to use formatting for transformer
old_preprocess_loop = """                for file_path in class_dir.rglob("*.msg"):
                    text = self._extract_text(file_path)
                    if text:
                        # Anonymisierung vor der Weiterverarbeitung
                        text = anonymize_th_koeln_names(text)
                        texts.append(text)
                        labels.append(label)"""

new_preprocess_loop = """                for file_path in class_dir.rglob("*.msg"):
                    if self.method == "transformer":
                        text = self._format_transformer_input(file_path)
                    else:
                        text = self._extract_text(file_path)
                        if text:
                            text = anonymize_th_koeln_names(text)

                    if text:
                        texts.append(text)
                        labels.append(label)"""

content = content.replace(old_preprocess_loop, new_preprocess_loop)

# Update predict method for transformer
old_predict_logic = """        text = self._extract_text(Path(file_path))
        if not text:
            raise ValueError(f"Konnte Text aus {file_path} nicht extrahieren.")

        # Anonymisierung vor der Merkmalsextraktion
        text = anonymize_th_koeln_names(text)
        X = self.get_features([text], train=False)
        y_pred = self.classifier.predict(X)[0]
        y_prob = self.classifier.predict_proba(X)[0]"""

new_predict_logic = """        if self.method == "transformer":
            text = self._format_transformer_input(Path(file_path))
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            self.classifier.eval()
            with torch.no_grad():
                outputs = self.classifier(inputs["input_ids"], inputs["attention_mask"])
                probs = torch.softmax(outputs, dim=1)[0]
                y_pred = torch.argmax(probs).item()
                y_prob = probs.numpy()
        else:
            text = self._extract_text(Path(file_path))
            if not text:
                raise ValueError(f"Konnte Text aus {file_path} nicht extrahieren.")
            text = anonymize_th_koeln_names(text)
            X = self.get_features([text], train=False)
            y_pred = self.classifier.predict(X)[0]
            y_prob = self.classifier.predict_proba(X)[0]"""

content = content.replace(old_predict_logic, new_predict_logic)

path.write_text(content)
