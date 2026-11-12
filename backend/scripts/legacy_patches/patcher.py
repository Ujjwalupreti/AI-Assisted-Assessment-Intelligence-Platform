import re
import sys

def patch_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add database import if missing
        if 'from database import' not in content:
            if 'import json' in content:
                content = content.replace('import json', 'import json\nfrom database import get_db')
            elif 'import os' in content:
                content = content.replace('import os', 'import os\nfrom database import get_db')
            else:
                content = 'from database import get_db\n' + content

        # Replace 'Model.query' with 'db.query(Model)'
        content = re.sub(r'Question\.query', r'db.query(Question)', content)
        content = re.sub(r'DocumentChunk\.query', r'db.query(DocumentChunk)', content)
        content = re.sub(r'QuestionAiAnalysis\.query', r'db.query(QuestionAiAnalysis)', content)

        # Replace 'db.session.xxx' with 'db.xxx'
        content = re.sub(r'db\.session\.flush\(\)', r'db.flush()', content)
        content = re.sub(r'db\.session\.add\(', r'db.add(', content)
        content = re.sub(r'db\.session\.commit\(\)', r'db.commit()', content)
        content = re.sub(r'db\.session\.rollback\(\)', r'db.rollback()', content)

        # Inject db = next(get_db()) into specific defs
        defs_to_inject = ['_find_best_question', '_find_removable_questions', '_find_low_quality_questions', 'store_document_chunks', 'retrieve_context', 'save_qis_analysis']
        
        for d in defs_to_inject:
            # We match the def signature, and optional docstring, then inject
            pattern = r'(def\s+' + d + r'\s*\([^)]*\)(?:\s*->\s*[^:]+)?:.*?)\n(\s+)([\'\"]{3}.*?[\'\"]{3}\n\s+)?'
            replacement = r'\1\n\2\3db = next(get_db())\n\2'
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Patched {filepath}')
    except Exception as e:
        print(f'Failed to patch {filepath}: {e}')

patch_file('ai/recommender.py')
patch_file('ai/rag/retriever.py')
patch_file('ai/qis_persistence.py')
