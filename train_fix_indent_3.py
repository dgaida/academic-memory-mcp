from pathlib import Path

path = Path("mcp_university/classifier/train.py")
content = path.read_text()

# Fix indent for cv_results assignment
bad_cv = """        if args.method != "transformer":
            # CV Ergebnisse für den Bericht vorbereiten
            cv_results = {
                'best_params': grid_search.best_params_,
                'best_score': grid_search.best_score_,
                'results': grid_search.cv_results_
            }"""

good_cv = """            if args.method != "transformer":
                # CV Ergebnisse für den Bericht vorbereiten
                cv_results = {
                    'best_params': grid_search.best_params_,
                    'best_score': grid_search.best_score_,
                    'results': grid_search.cv_results_
                }"""

content = content.replace(bad_cv, good_cv)
path.write_text(content)
