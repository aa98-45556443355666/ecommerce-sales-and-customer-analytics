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

    rows = []

    for cust_id in range(1, count+1):
        signup_date = fake.date_between(start_date="-5y", end_date="today")

        rows.append(
            {
                "customer_id": cust_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.email(),
                "gender": random.choice(
                    ["Male", "Female", "Other"]
                ),
                "date_of_birth": fake.date_of_birth(
                    minimum_age=18,
                    maximum_age=81,
                ),
                "city": fake.city(),
                "state": random.choice(INDIAN_STATES),
                "country": "India",
                "signup_date": signup_date
            }

        )

    df = pd.DataFrame(rows)

    # Introduce a small amount of anlomaly in data
    duplicate_indexes = rng.choice(
        df.index,
        size=max(1, int(count * 0.001)),
        replace=False,
    )

    duplicated_rows = df.loc[duplicate_indexes].copy()
    df = pd.concat(
        [df, duplicated_rows],
        ignore_index=True,
    )

    null_email_indexes = rng.choice(
        df.index,
        size=max(1, int(len(df) * 0.002)),
        replace=False,
    )

    df.loc[null_email_indexes, "email"] = None

    return df


def generate_products(count: int, fake: Faker, rng: np.random.Generator) -> pd.DataFrame:

    rows = []

    category_names = list(CATEGORIES.keys())

    for prod_id in range(1, count+1):
        category = random.choice(category_names)

        subcategory = random.choice(CATEGORIES[category])

        cost = round(float(rng.uniform(200, 50000)),
                     2,)
        price = round(
            cost * float(rng.uniform(1.15, 2.5)),
            2,
        )

        rows.append({
            "product_id": prod_id,
            "product_name": f"{fake.word().title()} "
            f"{subcategory}",
            "category": category,
            "subcategory": subcategory,
            "brand": fake.company(),
            "price": price,
            "cost": cost,

        })

    df = pd.DataFrame(rows)

    # Introduce a few missing categories.
    null_indexes = rng.choice(
        df.index,
        size=max(1, int(count * 0.001)),
        replace=False,
    )

    df.loc[null_indexes, "category"] = None

    return df


def generate_orders(count: int, cust_cnt: int, fake: Faker, rng: np.random.Generator) -> pd.DataFrame:

    cust_ids = rng.integers(1, cust_cnt+1, size=count)

    dates = pd.to_datetime(pd.Series(fake.date_between(
        start_date="-2y", end_date="today")for _ in range(count)))

    statuses = rng.choice(
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
    )

    payment_methods = rng.choice(
        [
            "UPI",
            "Credit Card",
            "Debit Card",
            "Net Banking",
            "COD",
        ],
        size=count,
    )

    df = pd.DataFrame(
        {
            "order_id": np.arange(1, count + 1),
            "customer_id": cust_ids,
            "order_date": dates,
            "order_status": statuses,
            "payment_method": payment_methods,
            "shipping_city": [
                fake.city() for _ in range(count)
            ],
            "shipping_state": rng.choice(
                INDIAN_STATES,
                size=count,
            ),
        }
    )

    # Add a small percentage of duplicated orders.
    duplicate_indexes = rng.choice(
        df.index,
        size=max(1, int(count * 0.0005)),
        replace=False,
    )

    duplicated_rows = df.loc[duplicate_indexes].copy()

    df = pd.concat(
        [df, duplicated_rows],
        ignore_index=True,
    )

    return df


def generate_order_items(order_count: int, product_count: int, product_prices: pd.Series, seed: int) -> pd.DataFrame:

    rows = []

    rng = np.random.default_rng(seed)

    item_id = 1

    for order_id in range(1, order_count + 1):

        number_of_items = int(
            rng.integers(1, 5)
        )

        product_ids = rng.choice(
            np.arange(1, product_count + 1),
            size=number_of_items,
            replace=False,
        )

        for product_id in product_ids:

            quantity = int(
                rng.integers(1, 5)
            )

            unit_price = float(
                product_prices.loc[product_id]
            )

            discount = round(
                float(
                    rng.choice(
                        [0, 0.05, 0.10, 0.15, 0.20]
                    )
                ),
                2,
            )

            rows.append(
                {
                    "item_id": item_id,
                    "order_id": order_id,
                    "product_id": int(product_id),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                }
            )

            item_id += 1

    return pd.DataFrame(rows)


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

    selected_items = order_items.loc[
        selected_indexes
    ].copy()

    reasons = [
        "Damaged",
        "Wrong Product",
        "Product Not Needed",
        "Late Delivery",
        "Quality Issue",
    ]

    returns = pd.DataFrame(
        {
            "return_id": np.arange(
                1,
                len(selected_items) + 1,
            ),
            "order_id": selected_items[
                "order_id"
            ].values,
            "product_id": selected_items[
                "product_id"
            ].values,
            "return_date": pd.Timestamp.today()
            - pd.to_timedelta(
                rng.integers(
                    1,
                    180,
                    size=len(selected_items),
                ),
                unit="D",
            ),
            "return_reason": rng.choice(
                reasons,
                size=len(selected_items),
            ),
        }
    )

    return returns


def save_dataset(df: pd.DataFrame, output_path: Path) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
    )


def save_sample(df: pd.DataFrame, output_path: Path, rows: int = 100) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.head(rows).to_csv(
        output_path,
        index=False,
    )


def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic e-commerce datasets."
        )
    )

    parser.add_argument(
        "--customers",
        type=int,
        default=None,
        help="Number of customers",
    )

    parser.add_argument(
        "--products",
        type=int,
        default=None,
        help="Number of products",
    )

    parser.add_argument(
        "--orders",
        type=int,
        default=None,
        help="Number of orders",
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to YAML configuration",
    )

    return parser.parse_args()


def main() -> None:

    args = parse_arguments()

    config = load_config(
        Path(args.config)
    )

    generation_config = config["generation"]

    seed = generation_config["seed"]

    customer_count = (
        args.customers
        if args.customers is not None
        else generation_config["customers"]
    )

    product_count = (
        args.products
        if args.products is not None
        else generation_config["products"]
    )

    order_count = (
        args.orders
        if args.orders is not None
        else generation_config["orders"]
    )

    output_dir = Path(
        config["data"]["output_dir"]
    )

    sample_dir = Path(
        config["data"]["sample_dir"]
    )

    fake = setup_randomness(seed)

    rng = np.random.default_rng(seed)

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

    product_prices = products.set_index(
        "product_id"
    )["price"]

    order_items = generate_order_items(
        order_count=order_count,
        product_count=product_count,
        product_prices=product_prices,
        seed=seed,
    )

    print("Generating returns...")

    returns = generate_returns(
        order_items,
        generation_config["return_rate"],
        seed=seed,
    )

    print("Saving datasets...")

    save_dataset(
        customers,
        output_dir / "customers.csv",
    )

    save_dataset(
        products,
        output_dir / "products.csv",
    )

    save_dataset(
        orders,
        output_dir / "orders.csv",
    )

    save_dataset(
        order_items,
        output_dir / "order_items.csv",
    )

    save_dataset(
        returns,
        output_dir / "returns.csv",
    )

    print("Saving sample datasets...")

    save_sample(
        customers,
        sample_dir / "customers_sample.csv",
    )

    save_sample(
        products,
        sample_dir / "products_sample.csv",
    )

    save_sample(
        orders,
        sample_dir / "orders_sample.csv",
    )

    save_sample(
        order_items,
        sample_dir / "order_items_sample.csv",
    )

    save_sample(
        returns,
        sample_dir / "returns_sample.csv",
    )

    print("\nData generation completed successfully.")

    print(f"Customers    : {len(customers):,}")
    print(f"Products     : {len(products):,}")
    print(f"Orders       : {len(orders):,}")
    print(f"Order Items  : {len(order_items):,}")
    print(f"Returns      : {len(returns):,}")


if __name__ == "__main__":
    main()
