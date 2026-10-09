from __future__ import annotations
import argparse
import random
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from faker import Faker

INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Keralam",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]

CATEGORIES = {
    "Electronics": [
        "Mobile",
        "Laptop",
        "Tablet",
        "Headphone",
        "Camera",
    ],
    "Fashion": [
        "Men Clothing",
        "Women Clothing",
        "Shoes",
        "Accessories",
    ],
    "Home": [
        "Furniture",
        "Kitchen",
        "Decor",
        "Appliance",
    ],
    "Beauty": [
        "Skincare",
        "Makeup",
        "Haircare",
        "Personal Care",
    ],
    "Sports": [
        "Fitness",
        "Outdoor",
        "Cycling",
        "Sportswear",
    ],
}

RETURN_REASONS = [
    "Damaged",
    "Wrong Product",
    "Product Not Needed",
    "Late Delivery",
    "Quality Issue",
]


def load_config(config_path: Path) -> dict:
    """Load project configuration from YAML"""
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def setup_randomness(seed: int) -> Faker:
    """Make generated data reproducible"""
    random.seed(seed)
    np.random.seed(seed)

    fake = Faker("en_IN")
    Faker.seed(seed)

    return fake


def generate_customers(count: int, fake: Faker, rng: np.random.Generator) -> pd.DataFrame:

    customers = pd.DataFrame(
        {
            "customer_id": np.arange(1, count + 1),
            "first_name": [
                fake.first_name()
                for _ in range(count)
            ],
            "last_name": [
                fake.last_name()
                for _ in range(count)
            ],
            "email": [
                fake.email()
                for _ in range(count)
            ],
            "gender": rng.choice(
                ["Male", "Female", "Other"],
                size=count,
            ),
            "date_of_birth": [
                fake.date_of_birth(
                    minimum_age=18,
                    maximum_age=81,
                )
                for _ in range(count)
            ],
            "city": [
                fake.city()
                for _ in range(count)
            ],
            "state": rng.choice(
                INDIAN_STATES,
                size=count,
            ),
            "country": "India",
            "signup_date": pd.to_datetime([
                fake.date_between(
                    start_date="-5y",
                    end_date="today",
                )
                for _ in range(count)
            ]),
        }
    )

    duplicate_count = max(1, int(count * 0.001))

    duplicate_indexes = rng.choice(
        customers.index,
        size=duplicate_count,
        replace=False,
    )

    customers = pd.concat(
        [
            customers,
            customers.loc[duplicate_indexes],
        ],
        ignore_index=True,
    )

    null_email_count = max(1, int(len(customers) * 0.002))

    null_email_indexes = rng.choice(
        customers.index,
        size=null_email_count,
        replace=False,
    )

    customers.loc[
        null_email_indexes,
        "email"
    ] = None

    return customers


def generate_products(count: int, fake: Faker, rng: np.random.Generator) -> pd.DataFrame:

    category_names = list(CATEGORIES.keys())

    category = rng.choice(
        category_names,
        size=count,
    )

    subcategories = [
        random.choice(CATEGORIES[c])
        for c in category
    ]

    cost = np.round(
        rng.uniform(200, 50000, size=count),
        2,
    )

    price = np.round(
        cost * rng.uniform(1.15, 2.5, size=count),
        2,
    )

    products = pd.DataFrame(
        {
            "product_id": np.arange(1, count + 1),
            "product_name": [
                f"{fake.word().title()} {sub}"
                for sub in subcategories
            ],
            "category": category,
            "subcategory": subcategories,
            "brand": [
                fake.company()
                for _ in range(count)
            ],
            "price": price,
            "cost": cost,
        }
    )

    null_count = max(1, int(count * 0.001))

    null_indexes = rng.choice(
        products.index,
        size=null_count,
        replace=False,
    )

    products.loc[
        null_indexes,
        "category"
    ] = None

    return products


def generate_orders(count: int, customer_count: int, fake: Faker, rng: np.random.Generator) -> pd.DataFrame:

    start_date = pd.Timestamp.today() - pd.DateOffset(
        years=2
    )

    end_date = pd.Timestamp.today()

    order_dates = pd.to_datetime(
        rng.integers(
            start_date.value // 10**9,
            end_date.value // 10**9,
            size=count,
        ),
        unit="s",
    ).normalize()

    orders = pd.DataFrame(
        {
            "order_id": np.arange(1, count + 1),
            "customer_id": rng.integers(
                1,
                customer_count + 1,
                size=count,
            ),
            "order_date": order_dates,
            "order_status": rng.choice(
                [
                    "Delivered",
                    "Shipped",
                    "Processing",
                    "Cancelled",
                ],
                size=count,
                p=[
                    0.72,
                    0.12,
                    0.10,
                    0.06,
                ],
            ),
            "payment_method": rng.choice(
                [
                    "UPI",
                    "Credit Card",
                    "Debit Card",
                    "Net Banking",
                    "COD",
                ],
                size=count,
            ),
            "shipping_city": [
                fake.city()
                for _ in range(count)
            ],
            "shipping_state": rng.choice(
                INDIAN_STATES,
                size=count,
            ),
        }
    )

    duplicate_count = max(
        1,
        int(count * 0.0005),
    )

    duplicate_indexes = rng.choice(
        orders.index,
        size=duplicate_count,
        replace=False,
    )

    orders = pd.concat(
        [
            orders,
            orders.loc[duplicate_indexes],
        ],
        ignore_index=True,
    )

    return orders


def generate_order_items(orders: pd.DataFrame, products: pd.DataFrame, seed: int) -> pd.DataFrame:

    rng = np.random.default_rng(seed)

    order_ids = orders["order_id"].drop_duplicates()

    item_counts = rng.integers(
        1,
        5,
        size=len(order_ids),
    )

    total_items = int(item_counts.sum())

    order_id_values = np.repeat(
        order_ids.to_numpy(),
        item_counts,
    )

    product_ids = rng.integers(
        1,
        len(products) + 1,
        size=total_items,
    )

    product_price_map = products.set_index(
        "product_id"
    )["price"]

    unit_prices = product_price_map.loc[
        product_ids
    ].to_numpy()

    quantities = rng.integers(
        1,
        5,
        size=total_items,
    )

    discounts = rng.choice(
        [0, 0.05, 0.10, 0.15, 0.20],
        size=total_items,
    )

    order_items = pd.DataFrame(
        {
            "item_id": np.arange(
                1,
                total_items + 1,
            ),
            "order_id": order_id_values,
            "product_id": product_ids,
            "quantity": quantities,
            "unit_price": unit_prices,
            "discount": discounts,
        }
    )

    return order_items


def generate_returns(order_items: pd.DataFrame, return_rate: float, seed: int) -> pd.DataFrame:

    rng = np.random.default_rng(seed)

    return_count = max(
        1,
        int(len(order_items) * return_rate),
    )

    selected_indexes = rng.choice(
        order_items.index,
        size=return_count,
        replace=False,
    )

    selected = order_items.loc[
        selected_indexes
    ].reset_index(drop=True)

    return_days = rng.integers(
        1,
        181,
        size=return_count,
    )

    return_dates = (
        pd.Timestamp.today().normalize()
        - pd.to_timedelta(
            return_days,
            unit="D",
        )
    )

    returns = pd.DataFrame(
        {
            "return_id": np.arange(
                1,
                return_count + 1,
            ),
            "order_id": selected["order_id"],
            "product_id": selected["product_id"],
            "return_date": return_dates,
            "return_reason": rng.choice(
                RETURN_REASONS,
                size=return_count,
            ),
        }
    )

    return returns


def save_csv(df: pd.DataFrame, path: Path) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        path,
        index=False,
    )


def save_sample(df: pd.DataFrame, path: Path, sample_size: int) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.head(sample_size).to_csv(
        path,
        index=False,
    )


def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic e-commerce data."
        )
    )

    parser.add_argument(
        "--customers",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--products",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--orders",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
    )

    return parser.parse_args()


def main() -> None:

    args = parse_arguments()

    config = load_config(
        Path(args.config)
    )

    generation = config["generation"]
    data_config = config["data"]

    seed = generation["seed"]

    customer_count = (
        args.customers
        if args.customers is not None
        else generation["customers"]
    )

    product_count = (
        args.products
        if args.products is not None
        else generation["products"]
    )

    order_count = (
        args.orders
        if args.orders is not None
        else generation["orders"]
    )

    fake = setup_randomness(seed)

    rng = np.random.default_rng(seed)

    raw_dir = Path(data_config["raw_dir"])
    sample_dir = Path(data_config["sample_dir"])
    sample_size = data_config["sample_rows"]

    print("Generating customers...")
    customers = generate_customers(
        customer_count,
        fake,
        rng,
    )

    print("Generating products...")
    products = generate_products(
        product_count,
        fake,
        rng,
    )

    print("Generating orders...")
    orders = generate_orders(
        order_count,
        customer_count,
        fake,
        rng,
    )

    print("Generating order items...")
    order_items = generate_order_items(
        orders,
        products,
        seed,
    )

    print("Generating returns...")
    returns = generate_returns(
        order_items,
        generation["return_rate"],
        seed,
    )

    print("Saving raw datasets...")

    save_csv(
        customers,
        raw_dir / "customers.csv",
    )

    save_csv(
        products,
        raw_dir / "products.csv",
    )

    save_csv(
        orders,
        raw_dir / "orders.csv",
    )

    save_csv(
        order_items,
        raw_dir / "order_items.csv",
    )

    save_csv(
        returns,
        raw_dir / "returns.csv",
    )

    print("Saving sample datasets...")

    save_sample(
        customers,
        sample_dir / "customers_sample.csv",
        sample_size,
    )

    save_sample(
        products,
        sample_dir / "products_sample.csv",
        sample_size,
    )

    save_sample(
        orders,
        sample_dir / "orders_sample.csv",
        sample_size,
    )

    save_sample(
        order_items,
        sample_dir / "order_items_sample.csv",
        sample_size,
    )

    save_sample(
        returns,
        sample_dir / "returns_sample.csv",
        sample_size,
    )

    print("\nGeneration complete.")
    print(f"Customers:   {len(customers):,}")
    print(f"Products:    {len(products):,}")
    print(f"Orders:      {len(orders):,}")
    print(f"Order Items: {len(order_items):,}")
    print(f"Returns:     {len(returns):,}")


if __name__ == "__main__":
    main()
