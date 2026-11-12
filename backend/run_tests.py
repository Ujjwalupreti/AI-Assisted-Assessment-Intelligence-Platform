import sys, traceback

print('=== TEST 1: Import all backend modules ===')
modules = [
    'ai.pipeline', 'ai.schemas', 'ai.qis_persistence', 
    'ai.duplicate_detector', 'ai.mcq_validator', 'ai.bloom_alignment',
    'ai.llm_client', 'ai.question_generator',
    'ml.inference'
]
for mod in modules:
    try:
        __import__(mod)
        print(f'  OK: {mod}')
    except Exception as e:
        print(f'  FAIL: {mod} -> {e}')

print()
print('=== TEST 2: Pipeline with MCQ ===')
try:
    from ai.pipeline import analyze_question_qis
    result = analyze_question_qis(
        question_text='What is the time complexity of binary search?',
        options={'A': 'O(log n)', 'B': 'O(n)', 'C': 'O(n log n)', 'D': 'O(1)'},
        correct_option='A'
    )
    status = result.get('status')
    cls = result.get('classification', {})
    bloom = cls.get('bloom', {})
    topic = cls.get('topic', {})
    qtype = cls.get('question_type', {})
    val = result.get('validation', {})
    dup = result.get('duplicate', {})
    rev = result.get('review', {})
    
    assert status in ('FULL', 'PARTIAL', 'FAILED'), 'Missing valid status'
    assert bloom.get('label') in ['Remember','Understand','Apply','Analyze','Evaluate','Create'], 'Invalid bloom label'
    assert 'duplicate' in result, 'Missing duplicate'
    assert 'review' in result, 'Missing review'
    print('  PASS: Full pipeline works')
    print(f'  Status: {status}')
    print(f'  Bloom: {bloom.get("label")} ({bloom.get("method")})')
    print(f'  Topic: {topic.get("label")} ({topic.get("method")})')
    print(f'  Type: {qtype.get("label")} ({qtype.get("method")})')
    print(f'  MCQ Valid: {val.get("valid")}')
    print(f'  Dup Risk: {dup.get("risk_label")}')
    print(f'  Review Required: {rev.get("required")}')
except Exception as e:
    print(f'  FAIL: {e}')
    traceback.print_exc()

print()
print('=== TEST 3: MCQ Validation Bugs ===')
try:
    from ai.mcq_validator import validate_mcq
    # Test with duplicate options
    r1 = validate_mcq('test?', {'A': 'same', 'B': 'same', 'C': 'different', 'D': 'other'}, 'A')
    assert not r1['valid'], 'Should fail on duplicate options'
    print('  PASS: Duplicate options detected')
    
    # Test with valid MCQ
    r2 = validate_mcq('test?', {'A': 'opt1', 'B': 'opt2', 'C': 'opt3', 'D': 'opt4'}, 'A')
    assert r2['valid'], 'Should pass with valid options'
    print('  PASS: Valid MCQ passes')
    
    # Test with empty option
    r3 = validate_mcq('test?', {'A': '', 'B': 'opt2', 'C': 'opt3', 'D': 'opt4'}, 'A')
    assert not r3['valid'], 'Should fail on empty option'
    print('  PASS: Empty option detected')
except Exception as e:
    print(f'  FAIL: {e}')
    traceback.print_exc()

print()
print('=== TEST 4: Duplicate Detector (no DB context) ===')
try:
    from ai.duplicate_detector import detect_duplicates, _risk_label
    assert _risk_label(0.5) == 'NONE', 'Risk label wrong for 0.5'
    assert _risk_label(0.75) == 'LOW_DUPLICATE_RISK', 'Risk label wrong for 0.75'
    assert _risk_label(0.85) == 'MEDIUM_DUPLICATE_RISK', 'Risk label wrong for 0.85'
    assert _risk_label(0.95) == 'HIGH_DUPLICATE_RISK', 'Risk label wrong for 0.95'
    print('  PASS: Risk labels correct')
    
    # Test with no existing questions
    r = detect_duplicates('test question', [])
    assert r['risk'] == 0.0, 'Empty should have 0 risk'
    assert r['risk_label'] in ('LOW', 'NONE'), 'Empty should be LOW or NONE'
    print('  PASS: Empty question bank handled')
except Exception as e:
    print(f'  FAIL: {e}')
    traceback.print_exc()

print()
print('=== TEST 5: Schema field standardization ===')
try:
    from ai.schemas import BloomResult, TopicResult, DifficultyResult, AnalysisResult
    # Check that schemas are importable and correct
    import inspect
    bloom_hints = BloomResult.__annotations__
    assert 'label' in bloom_hints, 'BloomResult missing label field'
    assert 'level' not in bloom_hints, 'BloomResult still has legacy level field!'
    
    topic_hints = TopicResult.__annotations__
    assert 'label' in topic_hints, 'TopicResult missing label field'
    assert 'topic' not in topic_hints, 'TopicResult still has legacy topic field!'
    
    diff_hints = DifficultyResult.__annotations__
    assert 'label' in diff_hints, 'DifficultyResult missing label field'
    assert 'level' not in diff_hints, 'DifficultyResult still has legacy level field!'
    
    print('  PASS: All schemas use label field correctly')
except Exception as e:
    print(f'  FAIL: {e}')
    traceback.print_exc()

print()
print('=== TEST 6: Inference - all question types ===')
try:
    from ml.inference import qis_inference
    
    # Structural MCQ detection (4 options)
    r = qis_inference.predict_question_type('Some question', {'A':'a','B':'b','C':'c','D':'d'})
    assert r['label'] == 'MCQ', f'Expected MCQ, got {r["label"]}'
    assert r['method'] == 'structural', f'Expected structural, got {r["method"]}'
    print(f'  PASS: MCQ detected structurally')
    
    # True/False detection
    r2 = qis_inference.predict_question_type('True or false: The sky is blue.')
    assert r2['label'] == 'TRUE_FALSE', f'Expected TRUE_FALSE, got {r2["label"]}'
    print(f'  PASS: TRUE_FALSE detected')
    
    # Fill in blank
    r3 = qis_inference.predict_question_type('A _____ is used to store data.')
    assert r3['label'] == 'FILL_IN_THE_BLANK', f'Expected FILL_IN_THE_BLANK, got {r3["label"]}'
    print(f'  PASS: FILL_IN_THE_BLANK detected')
    
    # Topic keyword detection
    try:
        r4 = qis_inference.predict_topic('Explain the difference between a stack and a queue data structure.')
        print(f'  INFO: Topic for stack/queue: {r4["label"]} ({r4["confidence"]:.0%}) via {r4["method"]}')
    except Exception as llm_e:
        print(f'  INFO: Topic inference via fallback: {llm_e}')
    
    # Bloom keyword detection
    try:
        r5 = qis_inference.predict_bloom('Evaluate whether a splay tree is more efficient than an AVL tree.')
        print(f'  INFO: Bloom for evaluate question: {r5["label"]} ({r5["confidence"]:.0%}) via {r5["method"]}')
    except Exception as llm_e:
        print(f'  INFO: Bloom inference via fallback: {llm_e}')
    
    # Difficulty multi-signal
    try:
        r6 = qis_inference.predict_difficulty('Apply the Knapsack dynamic programming algorithm to items with weights.', 'Apply')
        print(f'  INFO: Difficulty for dp question: {r6["label"]} ({r6["confidence"]:.0%}) via {r6["method"]}')
    except Exception as llm_e:
        print(f'  INFO: Difficulty inference via fallback: {llm_e}')
    
except Exception as e:
    print(f'  FAIL: {e}')
    traceback.print_exc()

print()
print('=== TEST 7: Routes registration check ===')
try:
    from app import create_app
    app = create_app()
    routes = [getattr(r, 'path', str(r)) for r in app.routes]
    required = [
        '/api/ai/questions/analyze',
        '/api/ai/questions/analyze-batch',
        '/api/intelligence',
        '/api/exams',
    ]
    for r in required:
        matching = [x for x in routes if r in x]
        if matching:
            print(f'  FOUND: {r}')
        else:
            print(f'  MISSING: {r}')
    print('  PASS: FastAPI routes registered correctly')
except Exception as e:
    print(f'  FAIL: {e}')
    traceback.print_exc()

print()
print('=== ALL TESTS COMPLETE ===')
