from pathlib import Path

path = Path("mcp_university/classifier/train.py")
content = path.read_text()

# Fix indent for logger and grid_search
bad_block = """        logger.info(f"Starte GridSearchCV mit 5-fold CV und 9 Experimenten für {args.method}...")
        grid_search = GridSearchCV(
            estimator=classifier.classifier,
            param_grid=param_grid,
            cv=5,
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(X, y)

        logger.info(f"Beste Parameter: {grid_search.best_params_}")
        logger.info(f"Bester Score: {grid_search.best_score_:.4f}")

        # Bestes Modell in den Classifier übernehmen
        classifier.classifier = grid_search.best_estimator_
        classifier.is_trained = True"""

good_block = """            logger.info(f"Starte GridSearchCV mit 5-fold CV und 9 Experimenten für {args.method}...")
            grid_search = GridSearchCV(
                estimator=classifier.classifier,
                param_grid=param_grid,
                cv=5,
                scoring='accuracy',
                n_jobs=-1,
                verbose=1
            )

            grid_search.fit(X, y)

            logger.info(f"Beste Parameter: {grid_search.best_params_}")
            logger.info(f"Bester Score: {grid_search.best_score_:.4f}")

            # Bestes Modell in den Classifier übernehmen
            classifier.classifier = grid_search.best_estimator_
            classifier.is_trained = True"""

content = content.replace(bad_block, good_block)
path.write_text(content)
