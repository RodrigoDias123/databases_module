from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from models import DATABASE_URL, Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Leave out of --autogenerate every table that is in the database but not in the models.

    Without this, the 65 Pagila tables we did not map (actor, payment and its partitions, ...)
    would come out as op.drop_table(). Their indexes and constraints are only compared when
    their table is included, so they are left out too.
    """
    if type_ == "table" and reflected and compare_to is None:
        return False
    # A foreign key from a mapped table to an unmapped one (customer.store_id -> store):
    # the models do not declare it, and without this it would come out as op.drop_constraint().
    if (
        type_ == "foreign_key_constraint"
        and reflected
        and object.referred_table.name not in target_metadata.tables
    ):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
