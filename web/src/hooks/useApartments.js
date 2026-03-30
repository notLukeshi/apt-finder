import { useState, useEffect, useCallback } from 'react';
import { fetchApartments, fetchWebsites, fetchTargets, fetchStats } from '../utils/api';

export function useApartments(initialFilters = {}) {
  const [apartments, setApartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(initialFilters);

  const loadApartments = useCallback(async () => {
    // Skip fetch if websites filter is not yet defined (wait for initial selection)
    if (filters.websites === undefined) {
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApartments(filters);
      setApartments(data.apartments);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadApartments();
  }, [loadApartments]);

  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  return { apartments, loading, error, filters, updateFilters, refresh: loadApartments };
}

export function useWebsites() {
  const [websites, setWebsites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWebsites()
      .then(setWebsites)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { websites, loading };
}

export function useTargets() {
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTargets()
      .then(setTargets)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { targets, loading };
}

export function useStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { stats, loading };
}
