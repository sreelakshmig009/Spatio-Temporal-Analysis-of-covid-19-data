# -*- coding: utf-8 -*-

import folium
import pandas as pd
from folium import plugins
from datetime import timedelta, date
import numpy as np


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


start_date = date(2020, 1, 22)
end_date = date(2021,1,1)
df = pd.DataFrame()
for single_date in daterange(start_date, end_date):
    fp = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/{}.csv".format(
        single_date.strftime("%m-%d-%Y")
    )
    df = df.append(pd.read_csv(fp).rename(columns={"Province_State":"Province/State","Country_Region":"Country/Region","Last_Update":"Last Update","Lat":"Latitude","Long_":"Longitude"}))


df["Province/State"] = df["Province/State"].fillna("N/A")
df2 = (
    df[["Province/State", "Country/Region", "Latitude", "Longitude"]]
    .dropna(axis=0)
    .groupby(["Province/State", "Country/Region"])
    .first()
)

df_acc = (
    df[
        [
            "Province/State",
            "Country/Region",
            "Last Update",
            "Confirmed",
            "Deaths",
            "Recovered",
        ]
    ]
    .set_index(["Province/State", "Country/Region"])
    .join(df2)
)


df3 = df2.copy()
df3["Last Update"] = start_date - timedelta(days=1)
df3["Confirmed"] = 0
df3["Deaths"] = 0
df3["Recovered"] = 0
df_acc = df_acc.append(df3)


df_acc["Last Update"] = pd.to_datetime(df_acc["Last Update"]).dt.date
df_acc = df_acc.reset_index()
df_acc["Location"] = df_acc["Province/State"] + ", " + df_acc["Country/Region"]
df_acc = df_acc.groupby(["Location", "Last Update"]).agg(
    {
        "Latitude": np.max,
        "Longitude": np.max,
        "Confirmed": np.max,
        "Deaths": np.max,
        "Recovered": np.max,
    }
)
df_acc = df_acc.sort_index()
new_index = pd.MultiIndex.from_product(df_acc.index.levels)
df_acc = df_acc.reindex(new_index, method="ffill").reset_index()



df_acc["Latitude"] = df_acc["Latitude"].astype(float)
df_acc["Longitude"] = df_acc["Longitude"].astype(float)


heat_df = df_acc[["Latitude", "Longitude", "Last Update","Confirmed","Deaths","Recovered"]].copy()


heat_df["Confirmed"] = heat_df["Confirmed"].astype(float).fillna(0)
heat_df["Deaths"] = heat_df["Deaths"].astype(float).fillna(0)
heat_df["Recovered"] = heat_df["Recovered"].astype(float).fillna(0)
heat_df["CurrentlyInfected"] = heat_df["Confirmed"]-heat_df["Recovered"]

heat_df = heat_df.dropna(axis=0, subset=["Latitude", "Longitude", "Confirmed"])
heat_df = heat_df.sort_values("Last Update")
heat_df["Last Update"] = pd.to_datetime(heat_df["Last Update"]).dt.strftime("%Y-%m-%d")
heat_df = heat_df[heat_df["Confirmed"] > 0]

heat_df["local_growth"] = heat_df.groupby(
    ["Latitude", "Longitude"]
).Confirmed.pct_change()
heat_df["local_growth"] = heat_df["local_growth"].clip(0).fillna(0)


limit_value = heat_df["Confirmed"].max()
alpha = 1000


confirmed_data = [
    [
        [
            row["Latitude"],
            row["Longitude"],
            alpha
            * np.log(1 + row["Confirmed"] / limit_value)
            / (1 + alpha * np.log(1 + row["Confirmed"] / limit_value)),
        ]
        for index, row in heat_df[heat_df["Last Update"] == i].iterrows()
    ]
    for i in heat_df["Last Update"].unique()
]

map_hmw = folium.Map(zoom_start=12)

hm = plugins.HeatMapWithTime(
    confirmed_data,
    index=list(heat_df["Last Update"].unique()),
    name="Current cases",
    auto_play=True,
    max_opacity=0.8,
)
hm.add_to(map_hmw)

ctrl = folium.LayerControl()
ctrl.add_to(map_hmw)


map_hmw.save("map.html")

