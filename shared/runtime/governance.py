from typing import Dict, Any
from shared.contracts.domain import MultiDomainBlueprint


class GovernancePolicy:

    MAX_AGENTS = 8

    MAX_DAG_DEPTH = 5

    MAX_BUDGET_USD = 0.50

    ALLOWED_DOMAINS = [
        "saas",
        "retail",
        "marketplace",
        "logistics",
        "manufacturing",
        "healthcare",
        "technology",
        "operations",
        "services",
        "other"
    ]


class RuntimeGovernance:
    """
    Enforces policies on dynamic workflows.
    """

    @staticmethod
    def validate_blueprint(
        blueprint: MultiDomainBlueprint
    ) -> Dict[str, Any]:

        issues = []

        # Agent count validation
        if len(
            blueprint.required_capabilities
        ) > GovernancePolicy.MAX_AGENTS:

            issues.append(
                f"Too many agents requested: "
                f"{len(blueprint.required_capabilities)}"
            )

        # Domain validation
        for domain in blueprint.domains:

            if (
                domain.domain
                not in GovernancePolicy.ALLOWED_DOMAINS
            ):

                issues.append(
                    f"Unsupported domain: "
                    f"{domain.domain}"
                )

        # Cost estimation
        estimated_cost = (
            len(blueprint.required_capabilities)
            * 0.05
        )

        if (
            estimated_cost
            > GovernancePolicy.MAX_BUDGET_USD
        ):

            issues.append(
                f"Estimated cost "
                f"${estimated_cost} exceeds "
                f"budget "
                f"${GovernancePolicy.MAX_BUDGET_USD}"
            )

        return {

            "is_allowed": len(issues) == 0,

            "issues": issues,

            "policy_version": "2.1.0"
        }

    @staticmethod
    def validate_execution(
        state,
        capability
    ) -> bool:

        if (
            len(state.active_tasks)
            > GovernancePolicy.MAX_AGENTS
        ):

            raise RuntimeError(
                "Too many active tasks"
            )

        return True
    
    
    @staticmethod
    def prune_workflow(
        blueprint: MultiDomainBlueprint
    ) -> MultiDomainBlueprint:
        
        blueprint = blueprint.copy(deep=True)

        if len(
            blueprint.required_capabilities
        ) > GovernancePolicy.MAX_AGENTS:

            blueprint.required_capabilities = (
                blueprint.required_capabilities[
                    :GovernancePolicy.MAX_AGENTS
                ]
            )

        return blueprint