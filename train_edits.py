from pathlib import Path

path = Path("mcp_university/classifier/train.py")
content = path.read_text()

# Update choices for method in main
content = content.replace('choices=["randomforest", "xgboost"]', 'choices=["randomforest", "xgboost", "transformer"]')

# Update training logic in main
old_train_logic = """        # Merkmale extrahieren
        X = classifier.get_features(texts, train=True)
        y = classifier.label_encoder.fit_transform(labels)

        # GridSearchCV Setup
        if args.method == "randomforest":"""

new_train_logic = """        # Labels encoden
        y = classifier.label_encoder.fit_transform(labels)
        num_classes = len(classifier.label_encoder.classes_)

        if args.method == "transformer":
            logger.info("Starte Transformer Fine-Tuning...")
            from mcp_university.classifier.engine import EmailTransformerClassifier
            classifier.classifier = EmailTransformerClassifier(args.embedding_model, num_classes)

            # Tokenisierung
            encodings = classifier.tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset = TensorDataset(encodings["input_ids"], encodings["attention_mask"], torch.tensor(y))
            loader = DataLoader(dataset, batch_size=8, shuffle=True)

            optimizer = torch.optim.AdamW(classifier.classifier.parameters(), lr=2e-5)
            criterion = torch.nn.CrossEntropyLoss()

            classifier.classifier.train()
            for epoch in range(3): # 3 Epochen als Standard
                total_loss = 0
                for batch in loader:
                    optimizer.zero_grad()
                    input_ids, mask, targets = batch
                    outputs = classifier.classifier(input_ids, mask)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                logger.info(f"Epoch {epoch+1}/3, Loss: {total_loss/len(loader):.4f}")

            classifier.is_trained = True
            cv_results = None # Keine CV für Transformer in diesem einfachen Loop
        else:
            # Merkmale extrahieren für klassische Modelle
            X = classifier.get_features(texts, train=True)

            # GridSearchCV Setup
            if args.method == "randomforest":"""

content = content.replace(old_train_logic, new_train_logic)

# Update the end of the GridSearch block to handle cv_results being None
content = content.replace("""        # CV Ergebnisse für den Bericht vorbereiten
        cv_results = {
            'best_params': grid_search.best_params_,
            'best_score': grid_search.best_score_,
            'results': grid_search.cv_results_
        }""", """        if args.method != "transformer":
            # CV Ergebnisse für den Bericht vorbereiten
            cv_results = {
                'best_params': grid_search.best_params_,
                'best_score': grid_search.best_score_,
                'results': grid_search.cv_results_
            }""")

path.write_text(content)
