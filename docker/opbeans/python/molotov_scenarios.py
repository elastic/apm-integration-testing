import io
import os
import random
import json
from urllib.parse import urljoin

from aiohttp import FormData
from molotov import scenario

SERVER_URL = os.environ.get('OPBEANS_SERVER_URL', 'http://localhost:8000')


@scenario(weight=10)
async def scenario_root(session):
    async with session.get(SERVER_URL) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_stats(session):
    async with session.get(join(SERVER_URL, 'api', 'stats')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=7)
async def scenario_products(session):
    async with session.get(join(SERVER_URL, 'api', 'products')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_products_top(session):
    async with session.get(join(SERVER_URL, 'api', 'products', 'top')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=6)
async def scenario_products_id(session):
    async with session.get(join(SERVER_URL, 'api', 'products', str(random.randint(1, 6)))) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=6)
async def scenario_products_id_customers(session):
    async with session.get(join(SERVER_URL, 'api', 'products', str(random.randint(1, 6)), 'customers')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=6)
async def scenario_products_id_customers_limit(session):
    async with session.get(join(SERVER_URL, 'api', 'products', str(random.randint(1, 6)), 'customers?limit=%d' % (random.randint(5, 11) * 10))) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_types(session):
    async with session.get(join(SERVER_URL, 'api', 'types')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_types_id(session):
    async with session.get(join(SERVER_URL, 'api', 'types', str(random.randint(1, 3)))) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_customers(session):
    async with session.get(join(SERVER_URL, 'api', 'customers')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_customers_id(session):
    async with session.get(join(SERVER_URL, 'api', 'customers', str(random.randint(1, 1000)))) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=2)
async def scenario_wrong_customers_id(session):
    async with session.get(join(SERVER_URL, 'api', 'customers', str(random.randint(5000, 10000)))) as resp:
        assert resp.status == 404, resp.status


@scenario(weight=8)
async def scenario_orders(session):
    async with session.get(join(SERVER_URL, 'api', 'orders')) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_orders_id(session):
    async with session.get(join(SERVER_URL, 'api', 'orders', str(random.randint(1, 1000)))) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=1)
async def scenario_orders_post(session):
    data = {
        'customer_id': random.randint(1, 1000),
        'lines': [],
    }
    for i in range(0, random.randint(1, 5)):
        data['lines'].append({
            'id': random.randint(1, 6),
            'amount': random.randint(1, 4)
        })
    async with session.post(join(SERVER_URL, 'api', 'orders'), data=json.dumps(data)) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=1)
async def scenario_orders_post_csv(session):
    customer_id = random.randint(1, 1000)
    lines = []
    for i in range(0, random.randint(1, 5)):
        lines.append(','.join(map(str, [
            random.randint(1, 6), random.randint(1, 4)
        ])))
    data = FormData()
    data.add_field('customer', str(customer_id))
    data.add_field(
        'file',
        io.BytesIO('\n'.join(lines).encode('utf8')),
        filename='data.csv',
        content_type='text/plain'
    )
    async with session.post(join(SERVER_URL, 'api', 'orders', 'csv'), data=data) as resp:
        assert resp.status == 200, resp.status


@scenario(weight=8)
async def scenario_oopsie(session):
    async with session.get(join(SERVER_URL, 'oopsie')) as resp:
        assert resp.status == 500


def join(base_url, *fragments):
        path = '/'.join(fragments)
        print(urljoin(base_url, path))
        return urljoin(base_url, path)