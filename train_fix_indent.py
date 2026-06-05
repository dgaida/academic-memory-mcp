from pathlib import Path

path = Path("mcp_university/classifier/train.py")
content = path.read_text()

bad_indent = """            # GridSearchCV Setup
            if args.method == "randomforest":
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20],
                'criterion': ['gini']
            }
        else:  # xgboost
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [2, 3],
                'learning_rate': [0.1]
            }"""

good_indent = """            # GridSearchCV Setup
            if args.method == "randomforest":
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20],
                    'criterion': ['gini']
                }
            else:  # xgboost
                param_grid = {
                    'n_estimators': [100, 200],
                    'max_depth': [2, 3],
                    'learning_rate': [0.1]
                }"""

content = content.replace(bad_indent, good_indent)
path.write_text(content)
