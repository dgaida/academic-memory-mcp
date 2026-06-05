from pathlib import Path

path = Path("mcp_university/classifier/train.py")
content = path.read_text()

# Update evaluate_and_save for transformer
old_eval_logic = """    # Vorhersagen
    X = classifier.get_features(texts, train=False)
    y_pred_idx = classifier.classifier.predict(X)
    y_pred = classifier.label_encoder.inverse_transform(y_pred_idx.astype(int))"""

new_eval_logic = """    # Vorhersagen
    if classifier.method == "transformer":
        classifier.classifier.eval()
        y_pred_idx = []
        with torch.no_grad():
            # Batchweise Verarbeitung für Evaluierung
            encodings = classifier.tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset = TensorDataset(encodings["input_ids"], encodings["attention_mask"])
            loader = DataLoader(dataset, batch_size=8)
            for batch in loader:
                ids, mask = batch
                outputs = classifier.classifier(ids, mask)
                preds = torch.argmax(outputs, dim=1)
                y_pred_idx.extend(preds.numpy())
        y_pred_idx = np.array(y_pred_idx)
    else:
        X = classifier.get_features(texts, train=False)
        y_pred_idx = classifier.classifier.predict(X)

    y_pred = classifier.label_encoder.inverse_transform(y_pred_idx.astype(int))"""

content = content.replace(old_eval_logic, new_eval_logic)

path.write_text(content)
