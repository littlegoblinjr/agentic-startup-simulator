def parse_llm_json(output):
    
    from json_repair import repair_json
    import json
    fixed = repair_json(output)
    return json.loads(fixed)