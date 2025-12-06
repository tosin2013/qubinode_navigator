______________________________________________________________________

## description: Generate a new DAG from template following ADR-0045 standards allowed-tools: Bash(./airflow/scripts/validate-dag.sh:\*), Read, Write argument-hint: \[dag-requirements\]

# Scaffold New DAG

You are helping create a new Qubinode Navigator Airflow DAG.

DAG requirements: $ARGUMENTS

First, review the DAG development standards:
@docs/adrs/adr-0045-dag-development-standards.md

Key standards to follow:

- Use triple double quotes (""") for bash_command, never '''
- DAG ID must be snake_case matching filename
- Use ASCII markers: \[OK\], \[ERROR\], \[WARN\], \[INFO\], \[SKIP\]
- No string concatenation in bash_command
- Include proper error handling and logging

Generate a DAG template that:

1. Follows all ADR-0045 standards
1. Includes proper documentation
1. Has appropriate tags for categorization
1. Uses the correct operators (BashOperator, KcliVMCreateOperator, etc.)
1. Includes example task dependencies

Place the new DAG in: airflow/dags/\<dag_name>.py

After generating, run validation:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && ./scripts/validate-dag.sh`
