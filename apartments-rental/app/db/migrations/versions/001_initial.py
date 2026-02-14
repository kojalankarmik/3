"""Initial migration with all models.

Revision ID: 001
Revises:
Create Date: 2024-02-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('role', sa.Enum('admin', 'manager', 'guest', name='userrole'), nullable=False, server_default='guest'),
        sa.Column('inviter_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['inviter_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=False)
    
    # Create apartments table
    op.create_table(
        'apartments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('address_short', sa.String(length=255), nullable=True),
        sa.Column('guests_max', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('beds_text', sa.String(length=100), nullable=True),
        sa.Column('features_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rules_short', sa.Text(), nullable=True),
        sa.Column('map_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_apartments_is_active', 'apartments', ['is_active'], unique=False)
    
    # Create apartment_media table
    op.create_table(
        'apartment_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('apartment_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['apartment_id'], ['apartments.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_apartment_media_apartment_id', 'apartment_media', ['apartment_id'], unique=False)
    
    # Create apartment_tags table
    op.create_table(
        'apartment_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('apartment_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['apartment_id'], ['apartments.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_apartment_tags_apartment_id', 'apartment_tags', ['apartment_id'], unique=False)
    
    # Create channel_posts table
    op.create_table(
        'channel_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('apartment_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.Enum('apartment', 'catalog', 'menu', 'faq', 'hot', name='channelpostkind'), nullable=False),
        sa.Column('channel_id', sa.String(length=50), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('last_published_at', sa.DateTime(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['apartment_id'], ['apartments.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_channel_posts_apartment_id', 'channel_posts', ['apartment_id'], unique=False)
    op.create_index('ix_channel_posts_kind', 'channel_posts', ['kind'], unique=False)
    
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('contact', sa.String(length=255), nullable=True),
        sa.Column('date_from', sa.String(length=10), nullable=True),
        sa.Column('date_to', sa.String(length=10), nullable=True),
        sa.Column('guests', sa.Integer(), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('budget_min', sa.Integer(), nullable=True),
        sa.Column('budget_max', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('new', 'in_progress', 'closed', 'spam', name='leadstatus'), nullable=False, server_default='new'),
        sa.Column('source_tag', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_leads_user_id', 'leads', ['user_id'], unique=False)
    op.create_index('ix_leads_status', 'leads', ['status'], unique=False)
    op.create_index('ix_leads_created_at', 'leads', ['created_at'], unique=False)
    
    # Create bookings table
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('created', 'confirmed', 'paid', 'canceled', name='bookingstatus'), nullable=False, server_default='created'),
        sa.Column('apartment_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('check_in', sa.String(length=10), nullable=True),
        sa.Column('check_out', sa.String(length=10), nullable=True),
        sa.Column('total_amount', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='RUB'),
        sa.Column('source_tag', sa.String(length=100), nullable=True),
        sa.Column('raw_payload_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['apartment_id'], ['apartments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_bookings_external_id'),
    )
    op.create_index('ix_bookings_apartment_id', 'bookings', ['apartment_id'], unique=False)
    op.create_index('ix_bookings_user_id', 'bookings', ['user_id'], unique=False)
    op.create_index('ix_bookings_status', 'bookings', ['status'], unique=False)
    op.create_index('ix_bookings_created_at', 'bookings', ['created_at'], unique=False)
    
    # Create referral_codes table
    op.create_table(
        'referral_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_referral_codes_code'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_referral_codes_user_id', 'referral_codes', ['user_id'], unique=False)
    op.create_index('ix_referral_codes_is_active', 'referral_codes', ['is_active'], unique=False)
    
    # Create referral_events table
    op.create_table(
        'referral_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referral_code_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.Enum('start', 'click', 'booking_created', 'booking_paid', name='referraleventtype'), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=True),
        sa.Column('meta_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['referral_code_id'], ['referral_codes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_referral_events_referral_code_id', 'referral_events', ['referral_code_id'], unique=False)
    op.create_index('ix_referral_events_type', 'referral_events', ['type'], unique=False)
    op.create_index('ix_referral_events_created_at', 'referral_events', ['created_at'], unique=False)
    
    # Create payouts table
    op.create_table(
        'payouts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referral_code_id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'paid', name='payoutstatus'), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['referral_code_id'], ['referral_codes.id'], ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id', name='uq_payouts_booking_id'),
    )
    op.create_index('ix_payouts_referral_code_id', 'payouts', ['referral_code_id'], unique=False)
    op.create_index('ix_payouts_status', 'payouts', ['status'], unique=False)
    
    # Create webhook_events table
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=100), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('raw_payload_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_events_provider', 'webhook_events', ['provider'], unique=False)
    op.create_index('ix_webhook_events_event_id', 'webhook_events', ['event_id'], unique=False)
    op.create_index('ix_webhook_events_received_at', 'webhook_events', ['received_at'], unique=False)


def downgrade() -> None:
    """Downgrade database."""
    
    op.drop_index('ix_webhook_events_received_at', table_name='webhook_events')
    op.drop_index('ix_webhook_events_event_id', table_name='webhook_events')
    op.drop_index('ix_webhook_events_provider', table_name='webhook_events')
    op.drop_table('webhook_events')
    
    op.drop_index('ix_payouts_status', table_name='payouts')
    op.drop_index('ix_payouts_referral_code_id', table_name='payouts')
    op.drop_table('payouts')
    
    op.drop_index('ix_referral_events_created_at', table_name='referral_events')
    op.drop_index('ix_referral_events_type', table_name='referral_events')
    op.drop_index('ix_referral_events_referral_code_id', table_name='referral_events')
    op.drop_table('referral_events')
    
    op.drop_index('ix_referral_codes_is_active', table_name='referral_codes')
    op.drop_index('ix_referral_codes_user_id', table_name='referral_codes')
    op.drop_table('referral_codes')
    
    op.drop_index('ix_bookings_created_at', table_name='bookings')
    op.drop_index('ix_bookings_status', table_name='bookings')
    op.drop_index('ix_bookings_user_id', table_name='bookings')
    op.drop_index('ix_bookings_apartment_id', table_name='bookings')
    op.drop_table('bookings')
    
    op.drop_index('ix_leads_created_at', table_name='leads')
    op.drop_index('ix_leads_status', table_name='leads')
    op.drop_index('ix_leads_user_id', table_name='leads')
    op.drop_table('leads')
    
    op.drop_index('ix_channel_posts_kind', table_name='channel_posts')
    op.drop_index('ix_channel_posts_apartment_id', table_name='channel_posts')
    op.drop_table('channel_posts')
    
    op.drop_index('ix_apartment_tags_apartment_id', table_name='apartment_tags')
    op.drop_table('apartment_tags')
    
    op.drop_index('ix_apartment_media_apartment_id', table_name='apartment_media')
    op.drop_table('apartment_media')
    
    op.drop_index('ix_apartments_is_active', table_name='apartments')
    op.drop_table('apartments')
    
    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_table('users')