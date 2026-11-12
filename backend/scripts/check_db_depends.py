import os
import ast

def find_missing_db_depends(directory):
    missing_endpoints = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read(), filename=filepath)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                # Check if it has a decorator that looks like a route (e.g., @exam_bp.get)
                                is_route = False
                                for decorator in node.decorator_list:
                                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                                        if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                            is_route = True
                                            break
                                if is_route:
                                    # Check if one of the arguments is Depends(get_db)
                                    has_db = False
                                    for arg in node.args.args:
                                        if arg.annotation and isinstance(arg.annotation, ast.Name) and arg.annotation.id == 'Session':
                                            has_db = True
                                        elif arg.arg == 'db':
                                            has_db = True
                                    if not has_db:
                                        missing_endpoints.append(f"{file}: {node.name}")
                    except Exception as e:
                        pass
    return missing_endpoints

if __name__ == "__main__":
    missing = find_missing_db_depends('c:\\Users\\Hp\\Downloads\\PRoject\\ai_project_copy\\backend\\routes')
    for m in missing:
        print(m)
