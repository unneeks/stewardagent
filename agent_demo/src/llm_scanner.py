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
        
        if 'cast(' in sql_lower:
            risks.append("CAST detected: Potential precision loss or type mismatch.")
        if 'coalesce(' in sql_lower or 'ifnull(' in sql_lower:
            risks.append("COALESCE detected: Potential obfuscation of null values.")
        if ' join ' in sql_lower:
            risks.append("JOIN detected: Potential fan-out or row loss risk.")
            
        return risks
