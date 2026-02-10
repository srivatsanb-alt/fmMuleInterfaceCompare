"""added hwid to trips

Revision ID: 81aad0db6156
Revises: 75db3d4e0422
Create Date: 2024-09-25 18:14:30.322190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '81aad0db6156'
down_revision: Union[str, None] = '75db3d4e0422'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Utility functions for idempotent migrations
def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name, index_name):
    """Check if an index exists on a table"""
    inspector = inspect(op.get_bind())
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def foreign_key_exists(table_name, constraint_name=None, column_name=None, referenced_table=None, referenced_column=None):
    """Check if a foreign key constraint exists"""
    inspector = inspect(op.get_bind())
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    for fk in foreign_keys:
        if constraint_name and fk.get('name') == constraint_name:
            return True
        if (column_name and referenced_table and referenced_column and 
            column_name in fk.get('constrained_columns', []) and
            fk.get('referred_table') == referenced_table and
            referenced_column in fk.get('referred_columns', [])):
            return True
    return False


def get_foreign_key_constraint_name(table_name, column_name, referenced_table, referenced_column):
    """Get the name of a foreign key constraint"""
    inspector = inspect(op.get_bind())
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    for fk in foreign_keys:
        if (column_name in fk.get('constrained_columns', []) and
            fk.get('referred_table') == referenced_table and
            referenced_column in fk.get('referred_columns', [])):
            return fk.get('name')
    return None


def safe_add_column(table_name, column, check_exists=True):
    """Safely add a column if it doesn't exist"""
    if check_exists and column_exists(table_name, column.name):
        return False
    op.add_column(table_name, column)
    return True


def safe_drop_column(table_name, column_name, check_exists=True):
    """Safely drop a column if it exists"""
    if check_exists and not column_exists(table_name, column_name):
        return False
    op.drop_column(table_name, column_name)
    return True


def safe_create_index(index_name, table_name, columns, unique=False, check_exists=True):
    """Safely create an index if it doesn't exist"""
    if check_exists and index_exists(table_name, index_name):
        return False
    op.create_index(index_name, table_name, columns, unique=unique)
    return True


def safe_drop_index(index_name, table_name, check_exists=True):
    """Safely drop an index if it exists"""
    if check_exists and not index_exists(table_name, index_name):
        return False
    op.drop_index(index_name, table_name=table_name)
    return True


def safe_create_foreign_key(constraint_name, source_table, referent_table, local_cols, remote_cols, check_exists=True):
    """Safely create a foreign key constraint if it doesn't exist"""
    if check_exists and foreign_key_exists(source_table, column_name=local_cols[0], referenced_table=referent_table, referenced_column=remote_cols[0]):
        return False
    op.create_foreign_key(constraint_name, source_table, referent_table, local_cols, remote_cols)
    return True


def safe_drop_foreign_key(constraint_name, table_name, check_exists=True):
    """Safely drop a foreign key constraint if it exists"""
    if check_exists and not foreign_key_exists(table_name, constraint_name=constraint_name):
        return False
    op.drop_constraint(constraint_name, table_name, type_='foreignkey')
    return True


def upgrade() -> None:
    # Safely add sherpa_hwid column if it doesn't exist
    safe_add_column('trips', sa.Column('sherpa_hwid', sa.String(), nullable=True))
    
    # Safely drop booking_time_index if it exists
    safe_drop_index('booking_time_index', 'trips')
    
    # Safely create sherpa_hwid index if it doesn't exist
    safe_create_index('ix_trips_sherpa_hwid', 'trips', ['sherpa_hwid'], unique=False)
    
    # Safely create foreign key constraint if it doesn't exist
    safe_create_foreign_key(None, 'trips', 'sherpas', ['sherpa_hwid'], ['hwid'])


def downgrade() -> None:
    # Get the actual foreign key constraint name and drop it if it exists
    constraint_name = get_foreign_key_constraint_name('trips', 'sherpa_hwid', 'sherpas', 'hwid')
    if constraint_name:
        safe_drop_foreign_key(constraint_name, 'trips')
    
    # Safely drop sherpa_hwid index if it exists
    safe_drop_index('ix_trips_sherpa_hwid', 'trips')
    
    # Safely recreate booking_time_index if it doesn't exist
    safe_create_index('booking_time_index', 'trips', ['booking_time'], unique=False)
    
    # Safely drop sherpa_hwid column if it exists
    safe_drop_column('trips', 'sherpa_hwid')
