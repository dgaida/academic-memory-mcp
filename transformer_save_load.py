from pathlib import Path

path = Path("mcp_university/classifier/engine.py")
content = path.read_text()

# Update save method for transformer
old_save_data = """        data = {
            "mode": self.mode,
            "method": self.method,
            "embedding_model_name": self.embedding_model_name,
            "tfidf_vectorizer": self.tfidf_vectorizer,
            "classifier": self.classifier,
            "label_encoder": self.label_encoder,
            "is_trained": self.is_trained
        }"""

new_save_data = """        if self.method == "transformer":
            # Transformer Modelle separat speichern oder State Dict nutzen
            classifier_data = {
                "state_dict": self.classifier.state_dict(),
                "config": {
                    "model_name": self.embedding_model_name,
                    "num_classes": len(self.label_encoder.classes_)
                }
            }
        else:
            classifier_data = self.classifier

        data = {
            "mode": self.mode,
            "method": self.method,
            "embedding_model_name": self.embedding_model_name,
            "tfidf_vectorizer": self.tfidf_vectorizer,
            "classifier": classifier_data,
            "label_encoder": self.label_encoder,
            "is_trained": self.is_trained
        }"""

content = content.replace(old_save_data, new_save_data)

# Update load method for transformer
old_load_logic = """        self.classifier = data["classifier"]"""

new_load_logic = """        if self.method == "transformer":
            c_data = data["classifier"]
            self.classifier = EmailTransformerClassifier(
                c_data["config"]["model_name"],
                c_data["config"]["num_classes"]
            )
            self.classifier.load_state_dict(c_data["state_dict"])
            self.tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name)
        else:
            self.classifier = data["classifier"]"""

content = content.replace(old_load_logic, new_load_logic)

path.write_text(content)
