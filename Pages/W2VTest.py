import streamlit as st
import pandas as pd
import time
import datetime
import matplotlib.pyplot as plt
import numpy as np
import re
from Dataprocessing import w2v_gensim, KMeans as km
import gensim.models

from sklearn.decomposition import IncrementalPCA    # inital reduction
from sklearn.manifold import TSNE                   # final reduction


class Model_Test():
    def __init__(self):
        #Lade das Zutatenverzeichnis und das Kontrollframe zutatenDf
        self.zutaten_verzeichnis = pd.read_csv("Data/Doku_wordListNoAmount.csv", sep= "|", header=None)
        self.zutatenDf = pd.read_csv("Data/zutatenDf.csv", sep="|", header = 0)
        self.zutatenDf = self.zutatenDf.drop("Menge", axis=1)

    def body(self): 
        #dataset = st.sidebar.selectbox("Datensatz", ["Korpus mit Sonderzeichen", "Korpus ohne Sonderzeichen"])
        #if dataset == "Korpus mit Sonderzeichen":
        st.title("Modell Test")
        st.markdown("Für die Modelltests sind die _Trainingsepochen_ des Modells, die genutzte _Wortfenstergröße_ und die projizierten _Dimensionen_ anpassbar.")
        st.markdown("Das Ergebnis des Modelltrainings ist eine Anordnung der Wörter aus den Rezepten im zweidimensionalen Raum.")
        st.markdown("Die _Clusteranzahl_ bestimmt, in wie viele Cluster die ausgewerten Wörter eingeteilt werden. Die Ergebnisse des Clustering sind unter _Auswertungsergebnisse_ abgebildet.")
        dataset = pd.read_csv("Data/Doku_corpusNoAmount.csv", sep= "|", header=None)

        no_iterations = st.sidebar.slider("Anzahl Trainingsepochen", min_value=1, value= 5, max_value=10)
        window_size = st.sidebar.slider("Wortfenstergröße", min_value=1, value=2, max_value=10)
        dimensions = st.sidebar.slider("Dimensionen", min_value=1, value=300, max_value=1200,step=300)
        no_cluster = st.sidebar.selectbox("Anzahl Cluster",options=[2,5,10,20,40,50,70,100,200], index=2)

        results = None
        if st.button("Starte Testlauf"):
            results = self.run_test(dataset, no_iterations, no_cluster, window_size, dimensions)
            st.text("Anordnung der Wörter im zweidimensionalen Raum")
            plt.scatter(results[2].x,results[2].y)
            st.pyplot()
            

    def plotting(self, df):
        fig, ax = plt.subplots()

        PADDING = 1.0
        x_axis_min = np.amin(df, axis=0)[0] - PADDING
        y_axis_min = np.amin(df, axis=0)[1] - PADDING
        x_axis_max = np.amax(df, axis=0)[0] + PADDING
        y_axis_max = np.amax(df, axis=0)[1] + PADDING
        
        plt.xlim(x_axis_min,x_axis_max)
        plt.ylim(y_axis_min,y_axis_max)
        plt.rcParams["figure.figsize"] = (10,10)

        
        return plt


    #Methode zum Aufrufen des Tests
    def run_test(self, dataset, no_iterations = 5, cluster_amount=5, window_size=2, dimensions = 300):
        input_parameters = pd.DataFrame(data=[no_iterations,window_size, dimensions, cluster_amount],columns =["Parameter"], index=["Iterationen", "Fenstergröße", "Dimensionen","Clusteranzahl"])
        st.dataframe(input_parameters)

        #Trainiere das Word2Vec Modell
        model_trainer = w2v_gensim.W2V()

        model_trainer.load_data(dataset)

        model_trainer.buildSentences()
        w2v=None
        with st.spinner("Modelltraining"):
            try:
                w2v=pd.read_csv("Data/gensim_w2v_"+str(no_iterations)+"_"+str(window_size)+"_"+str(dimensions)+".csv", header=0, sep="|", index_col=0)
            except :
                model_trainer.train_model(no_iterations,window_size, dimensions)
                w2v = model_trainer.save_vectors(no_iterations, window_size, dimensions)

        #Cluster die Vektoren aus dem Word2Vec Modell
        cluster_data = w2v[["x","y"]]
        kmeans = km.KMeans()
        with st.spinner("Clustering"):
            try:
                w2v = pd.read_csv("Data/w2v_full_results_"+str(no_iterations)+"_"+str(window_size)+"_"+str(cluster_amount)+"_"+str(dimensions)+".csv", header=0, sep="|", index_col=0)
            except:
                zuordnung = kmeans.run_manual_k(cluster_amount, cluster_data)
                w2v["Cluster"] = zuordnung["assigned to"]
                w2v.to_csv("Data/w2v_full_results_"+str(no_iterations)+"_"+str(window_size)+"_"+str(cluster_amount)+"_"+str(dimensions)+".csv", header=True, sep="|", index=True)

        #Erzeugen eines DataFrames zur Erzeugung der Kontrollergebnisse
        try:
            results = pd.read_csv("Data/w2v_cluster_results_"+str(no_iterations)+"_"+str(window_size)+"_"+str(cluster_amount)+"_"+str(dimensions)+".csv", header=0, sep="|", index_col=0)
        except:
            clusterlist = w2v["Cluster"].unique()
            results = pd.DataFrame(index=[clusterlist], columns=["Zugeordnete Wörter", "Daraus Bezeichnungen", "Reinheit"])
            for cluster in clusterlist:
                c_frame= w2v.loc[w2v["Cluster"]==cluster] 
                match_list = []
                for index, row in c_frame.iterrows():
                    if row["labels"] in list(self.zutatenDf["Zuordnung"]):
                        match_list.append(row["labels"])
                    
                results["Zugeordnete Wörter"][cluster] = len(c_frame)
                results["Daraus Bezeichnungen"][cluster] = len(match_list)
                results["Reinheit"][cluster] = round((len(match_list)/len(c_frame))*100,1)
            
            results = results.sort_index()
            new_indexes = []
            for index in list(results.index): 
                new_indexes.append("Cluster "+str(index[0]))
            results.index = new_indexes

            results.to_csv("Data/w2v_cluster_results_"+str(no_iterations)+"_"+str(window_size)+"_"+str(cluster_amount)+"_"+str(dimensions)+".csv", header=True, sep="|", index=True)

        #Ausgabe der Testläufe des Word2Vec Algorithmus
        result_index = ["Maximum", "Durchschnitt", "Minimum", "Über 50", "Unter 10"]
        result_data = [results["Reinheit"].max(), results["Reinheit"].mean(), results["Reinheit"].min(), 
                        len(results[results["Reinheit"] > 50]), len(results[results["Reinheit"] < 10])]
        result_zusammenfassung = pd.DataFrame(data=result_data, index=result_index, columns=["Reinheit"])
        return [results, result_zusammenfassung, w2v]

        # text = st.empty()
        # st.write(results)        
        # max = results["Hitrate"].max()
        # st.write("Max "+str(max))
        # avg = results["Hitrate"].mean()
        # st.write("Avg "+str(avg))
        # over50 = len(results[results["Hitrate"] > 50])
        # st.write(over50)
        # min = results["Hitrate"].min()
        # st.write("Min "+str(min))
        # under10 = len(results[results["Hitrate"] < 10])
        # st.write(under10)
            
        