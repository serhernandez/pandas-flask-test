from iso639 import Lang
from flask import Flask, render_template, request

import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.close("all")

pd.options.display.float_format = '{:.0f}'.format

movie_df = pd.read_csv('tmdb_5000_movies.csv')
movie_df.dropna()
credit_df = pd.read_csv('tmdb_5000_credits.csv')
credit_df.dropna()

combined_df = movie_df.merge(credit_df, how='inner', left_on='id', right_on='movie_id')
trimmed_df = combined_df[combined_df['budget'] > 0].drop(['homepage', 'keywords', 'overview', 'tagline', 'movie_id', 'title_y'], axis=1).sort_values(by='budget', ascending=False)

trimmed_df = trimmed_df.query('original_language != "xx"') #Ignoring xx as this is considered "no language"
trimmed_df['release_year'] = trimmed_df['release_date'].apply(lambda x: x.split("-")[0])
trimmed_df['crew_count'] = trimmed_df['crew'].apply(lambda x: len(json.loads(x)))
trimmed_df['cast_count'] = trimmed_df['cast'].apply(lambda x: len(json.loads(x)))
trimmed_df['credits_count'] = trimmed_df['crew_count'] + trimmed_df['cast_count']
trimmed_df = trimmed_df.replace('cn', 'zh') #Replacing instances of cn with zh as cn is an invalid ISO639-1 code and should be zh or zh-cn

budget_info_prelim = trimmed_df.groupby(['original_language', 'release_year'], as_index=False).agg(
avg_budget=pd.NamedAgg('budget', 'mean'), 
avg_credits=pd.NamedAgg('credits_count', 'mean'),
avg_cast=pd.NamedAgg('cast_count', 'mean'),
avg_crew=pd.NamedAgg('crew_count', 'mean'),
avg_runtime=pd.NamedAgg('runtime', 'mean'),
avg_revenue=pd.NamedAgg('revenue', 'mean')).sort_values(by=['original_language', 'release_year'])

for lang in budget_info_prelim['original_language'].unique():
    if len(budget_info_prelim[budget_info_prelim['original_language'] == lang]) == 1:
        budget_info_prelim = budget_info_prelim.query(f'original_language != "{lang}"') #Dropping languages with only 1 year for the sake of graph readability

budget_info_prelim['avg_budget'] = budget_info_prelim['avg_budget'] / 1000000
budget_info_prelim['avg_revenue'] = budget_info_prelim['avg_revenue'] / 1000000

langs = {Lang(lang).name:lang for lang in budget_info_prelim['original_language'].unique()}
secondaries = {
    'cast': ("Average # of Cast Members", "avg_cast"),
    'credits': ("Average # of Credits", "avg_credits"),
    'crew': ("Average # of Crew Members", "avg_crew"),
    'revenue': ("Average Revenue in USD (in Millions)", "avg_revenue"),
    'runtime': ("Average Runtime (in Minutes)", "avg_runtime")
}

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def graph():
    if request.method == "POST":
        lang = langs[request.form.get("language")]
        secondary = request.form.get("secondary")
        color_one = request.form.get("color1")
        color_two = request.form.get("color2")
    else:
        lang = "en"
        secondary = "credits"
        color_one = "blue"
        color_two = "red"
    
    budget_info = budget_info_prelim[budget_info_prelim['original_language'] == lang]

    if len(budget_info) > 20:
        interp = list(map(lambda x: str(int(x)), np.linspace(int(budget_info.iloc[0]['release_year']), int(budget_info.iloc[-1]['release_year']), 20)))
        budget_info = budget_info[budget_info.isin(interp).any(axis=1)].sort_values(by='release_year')

    plt.rcParams.update({'font.size': 15})
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('Release Year')
    ax1.set_ylabel('Average Budget in USD (in Millions)', color=color_one)
    ax1.plot(budget_info['release_year'], budget_info['avg_budget'], color=color_one, label="Average Budget")
    ax1.set_xticklabels(labels=budget_info['release_year'],rotation=90)

    plt.grid(True)
    plt.margins(0)

    ax2 = ax1.twinx()
    ax2.set_ylabel(secondaries[secondary][0], color=color_two)
    ax2.plot(budget_info['release_year'], budget_info[secondaries[secondary][1]], color=color_two, label=secondaries[secondary][0])
    
    fig.legend()

    fig.set_size_inches(16, 12)
    plt.savefig('static/images/plot.png', bbox_inches="tight", dpi=100)

    return render_template('test.html', lang=Lang(lang).name, langs=sorted(langs.keys()), url='/static/images/plot.png')