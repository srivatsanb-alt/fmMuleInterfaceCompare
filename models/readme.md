## Introduction ##

This directory contains the data models for our FastAPI application. These models are defined using SQLAlchemy and they are used to interact with the database.

## TimestampMixin ##

In the `base_models` file, there is class [TimestampMixin](base_models.py#classTimestampMixin) that automatically adds `created_at` and `updated_at` timestamp fields to any model that inherits from it.


