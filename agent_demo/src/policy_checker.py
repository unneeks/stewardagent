import yaml
import os

class PolicyChecker:
    def __init__(self):
        ontology_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "ontology", 
            "policy_ontology.yaml"
        )
        with open(ontology_path, "r") as f:
            self.ontology = yaml.safe_load(f)
            
    def check_policy_gaps(self, semantic_type: str, assigned_rule_description: str) -> list[str]:
        """
        Deterministically checks if the actual validations assigned cover the 
        required validations for the inferred semantic type.
        """
        gaps = []
        
        if semantic_type not in self.ontology:
            # If unknown, we can't deterministically verify policy
            return gaps
            
        required_validations = self.ontology[semantic_type].get('required_validations', [])
        
        # Simple heuristic to see if required validations are mentioned in the rule description
        desc_lower = assigned_rule_description.lower()
        
        for req in required_validations:
            # Very naive string matching to simulate checking if validation exists
            if req.replace('_', ' ') not in desc_lower and req not in desc_lower:
                gaps.append(f"Missing required validation: {req}")
                
        return gaps
