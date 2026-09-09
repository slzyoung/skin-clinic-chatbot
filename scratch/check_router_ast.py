import ast

router_file = "backend/app/rag/router.py"
try:
    with open(router_file, "r", encoding="utf-8") as f:
        code = f.read()
    ast.parse(code)
    print("✅ backend/app/rag/router.py has NO syntax/AST errors!")
except Exception as e:
    print(f"❌ Syntax Error in {router_file}: {e}")
