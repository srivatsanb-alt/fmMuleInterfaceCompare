"""Initial commit

Revision ID: 75db3d4e0422
Revises: 
Create Date: 2024-09-25 15:17:51.292323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '75db3d4e0422'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Utility functions for idempotent migrations
def constraint_exists(table_name, constraint_name):
    """Check if a constraint exists on a table"""
    inspector = inspect(op.get_bind())
    constraints = inspector.get_check_constraints(table_name)
    unique_constraints = inspector.get_unique_constraints(table_name)
    
    # Check check constraints
    for constraint in constraints:
        if constraint.get('name') == constraint_name:
            return True
    
    # Check unique constraints
    for constraint in unique_constraints:
        if constraint.get('name') == constraint_name:
            return True
    
    return False


def get_unique_constraint_name(table_name, column_name):
    """Get the name of a unique constraint on a column"""
    inspector = inspect(op.get_bind())
    unique_constraints = inspector.get_unique_constraints(table_name)
    
    for constraint in unique_constraints:
        if column_name in constraint.get('column_names', []):
            return constraint.get('name')
    return None


def safe_create_unique_constraint(constraint_name, table_name, columns, check_exists=True):
    """Safely create a unique constraint if it doesn't exist"""
    if check_exists and constraint_exists(table_name, constraint_name):
        return False
    op.create_unique_constraint(constraint_name, table_name, columns)
    return True


def safe_drop_constraint(constraint_name, table_name, constraint_type='unique', check_exists=True):
    """Safely drop a constraint if it exists"""
    if check_exists and not constraint_exists(table_name, constraint_name):
        return False
    op.drop_constraint(constraint_name, table_name, type_=constraint_type)
    return True


def upgrade() -> None:
    # Safely create unique constraint on exclusion_zones.zone_id if it doesn't exist
    # Since the original migration used None for constraint name, we'll use a default name
    safe_create_unique_constraint('uq_exclusion_zones_zone_id', 'exclusion_zones', ['zone_id'])


def downgrade() -> None:
    # Get the actual constraint name and drop it if it exists
    constraint_name = get_unique_constraint_name('exclusion_zones', 'zone_id')
    if constraint_name:
        safe_drop_constraint(constraint_name, 'exclusion_zones', 'unique')
