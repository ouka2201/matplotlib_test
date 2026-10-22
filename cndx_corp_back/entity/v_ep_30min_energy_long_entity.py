from sqlalchemy import BigInteger, Boolean, Column, MetaData, Numeric, String, Table, Text
from sqlalchemy.orm.base import Mapped

metadata = MetaData()


t_v_ep_30min_energy_long = Table(
    'v_ep_30min_energy_long', metadata,
    Column('corp_number', String(13)),
    Column('agreement_category', String(2)),
    Column('org_id', String(20)),
    Column('building_id', String(113)),
    Column('corp_name', String(100)),
    Column('building_name', String(100)),
    Column('ep_customer_number', String(16)),
    Column('supply_point_number', String(27)),
    Column('acquisition_date', String(8)),
    Column('time_slot', BigInteger),
    Column('time_label', Text),
    Column('electric_power_value', Numeric(25, 10)),
    Column('delete_flg', Boolean),
    schema='db_corp'
)
