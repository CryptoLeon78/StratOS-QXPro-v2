import { useQuery } from "@tanstack/react-query";

import {
  getCorrelationCoverage,
  getPortfolioBenchmark,
  getPortfolioBlocks,
  getPortfolioCorrelationSnapshot,
  getPortfolioCorrelations,
  getPortfolioProfiles,
  type CorrelationSource,
} from "@/api/endpoints/portfolio";

export function usePortfolioBlocks() {
  return useQuery({ queryKey: ["portfolio-blocks"], queryFn: getPortfolioBlocks });
}

export function usePortfolioProfiles() {
  return useQuery({ queryKey: ["portfolio-profiles"], queryFn: getPortfolioProfiles });
}

export function usePortfolioCorrelations(source: CorrelationSource, windowDays?: number) {
  return useQuery({
    queryKey: ["portfolio-correlations", source, windowDays],
    queryFn: () => getPortfolioCorrelations(source, windowDays),
  });
}

export function usePortfolioCorrelationSnapshot(source: CorrelationSource, windowDays?: number) {
  return useQuery({
    queryKey: ["portfolio-correlation-snapshot", source, windowDays],
    queryFn: () => getPortfolioCorrelationSnapshot(source, windowDays),
  });
}

export function usePortfolioBenchmark() {
  return useQuery({ queryKey: ["portfolio-benchmark"], queryFn: getPortfolioBenchmark });
}

export function useCorrelationCoverage(source: CorrelationSource) {
  return useQuery({
    queryKey: ["portfolio-correlation-coverage", source],
    queryFn: () => getCorrelationCoverage(source),
  });
}
