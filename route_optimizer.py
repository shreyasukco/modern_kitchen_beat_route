import numpy as np
import random
import streamlit as st
from scipy.spatial import distance_matrix
from geopy.distance import geodesic
from exceptions import RouteOptimizationError  # Fixed import

class RouteOptimizer:
    def two_opt_improved(self, route, dist_matrix):
        best = route.copy()
        improved = True
        while improved:
            improved = False
            for i in range(1, len(route) - 2):
                for j in range(i + 2, min(len(route), i + 15)):
                    a, b, c, d = best[i - 1], best[i], best[j - 1], best[j % len(best)]
                    current = dist_matrix[a, b] + dist_matrix[c, d]
                    potential = dist_matrix[a, c] + dist_matrix[b, d]
                    if potential < current:
                        best[i:j] = best[i:j][::-1]
                        improved = True
        return best

    def route_distance(self, route, dist_matrix):
        total = 0.0
        for i in range(len(route) - 1):
            total += dist_matrix[route[i], route[i+1]]
        return total

    @st.cache_data(show_spinner=True, max_entries=20)
    def optimize_single_beat(_self, coords):
        try:
            n = len(coords)
            if n < 2:
                return list(range(n))

            dist_matrix = distance_matrix(coords, coords)
            
            population_size = min(200, max(50, n * 2))
            generations = min(1000, max(100, n * 5))
            mutation_rate = max(0.01, min(0.1, 0.5 / n))

            def create_individual():
                individual = np.random.permutation(n)
                return _self.two_opt_improved(individual, dist_matrix)

            population = [create_individual() for _ in range(population_size)]
            progress_bar = st.progress(0)

            for gen in range(generations):
                population = sorted(population, key=lambda x: _self.route_distance(x, dist_matrix))
                next_gen = population[:10]
                
                while len(next_gen) < population_size:
                    p1, p2 = random.choices(population[:50], k=2)
                    a, b = sorted(random.sample(range(n), 2))
                    child = np.concatenate([
                        p2[~np.isin(p2, p1[a:b])],
                        p1[a:b]
                    ])
                    
                    if random.random() < mutation_rate:
                        i, j = random.sample(range(n), 2)
                        child[i], child[j] = child[j], child[i]
                    
                    child = _self.two_opt_improved(child, dist_matrix)
                    next_gen.append(child)
                
                population = next_gen
                progress_bar.progress((gen + 1) / generations)

            progress_bar.empty()
            return min(population, key=lambda x: _self.route_distance(x, dist_matrix))
            
        except Exception as e:
            raise RouteOptimizationError(f"Route optimization failed: {e}")

    def calculate_route_distance(self, sorted_df):
        try:
            total_distance = 0
            for i in range(1, len(sorted_df)):
                point1 = (sorted_df.iloc[i-1]["lat"], sorted_df.iloc[i-1]["longi"])
                point2 = (sorted_df.iloc[i]["lat"], sorted_df.iloc[i]["longi"])
                total_distance += geodesic(point1, point2).km
            return total_distance
        except Exception as e:
            raise RouteOptimizationError(f"Distance calculation failed: {e}")