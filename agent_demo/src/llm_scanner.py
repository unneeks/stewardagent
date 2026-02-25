import re

class LLMScanner:
    """
    Simulates LLM semantic reasoning and SQL parsing.
    Deterministic simulation for demo purposes based on simple heuristics.
    """
    
    def __init__(self):
        # Simulated semantic mapping memory
        self.semantic_mapping = {
            'income': 'income',
            'amount': 'loan_amount',
            'status': 'status',
            'id': 'id'
        }
        
    def infer_semantic_type(self, column_name: str, rule_description: str) -> str:
        """
        Simulates an LLM interpreting the semantic intent of a column based on name and rule context.
        """
        # Simplistic keyword matching to simulate LLM judgment
        text = f"{column_name} {rule_description}".lower()
        if 'income' in text:
            return 'income'
        elif 'amount' in text or 'loan' in text:
            return 'loan_amount'
        elif 'status' in text:
            return 'status'
        elif 'id' in text or 'identifier' in text:
            return 'id'
        return 'unknown'
        
    def analyze_sql_for_risks(self, sql_text: str) -> list[str]:
        """
        Simulates LLM detecting risky SQL transformations that might drop data or change semantics.
        """
        risks = []
        sql_lower = sql_text.lower()
        
        # Try real LLM if api key exists
        import os
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                
                prompt = f"""
                You are a data governance AI. Analyze the following SQL query for data quality or semantic risks.
                Specifically look for:
                1. Use of CAST() which might lose precision or hide invalid types.
                2. Use of COALESCE() or IFNULL() which might silently mask NULL values from being caught by downstream rules.
                3. Use of JOINs without proper deduplication which might cause row fan-outs or duplicate entries.
                
                SQL:
                ```sql
                {sql_text}
                ```
                
                If you find any of those 3 risks, just return exactly those risk sentences. E.g. "COALESCE detected: Potential obfuscation of null values."
                If NO risks, return "NO RISKS". Return ONLY a bulleted list of risks detected.
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                if "NO RISKS" not in response.text:
                    for line in response.text.split('\\n'):
                        line = line.strip().strip('-*').strip()
                        if line:
                            # Map standard responses back to agent logic strings for continuity if needed
                            if "CAST" in line.upper(): risks.append("CAST detected: Potential precision loss or type mismatch.")
                            elif "COALESCE" in line.upper(): risks.append("COALESCE detected: Potential obfuscation of null values.")
                            elif "JOIN" in line.upper(): risks.append("JOIN detected: Potential fan-out or row loss risk.")
                            else: risks.append(line)
                            
                    if risks:
                        return list(set(risks))
            except Exception as e:
                print(f"Failed to use real LLM: {e}. Falling back to mock logic.")
        
        # Fallback to Mock Logic
        if 'cast(' in sql_lower:
            risks.append("CAST detected: Potential precision loss or type mismatch.")
        if 'coalesce(' in sql_lower or 'ifnull(' in sql_lower:
            risks.append("COALESCE detected: Potential obfuscation of null values.")
        if ' join ' in sql_lower:
            risks.append("JOIN detected: Potential fan-out or row loss risk.")
            
        return risks
