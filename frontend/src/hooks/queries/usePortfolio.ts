import { useQuery } from "@tanstack/react-query";

import {
  getPortfolioBenchmark,
  getPortfolioBlocks,
  getPortfolioCorrelations,
  getPortfolioProfiles,
} from "@/api/endpoints/portfolio";

export function usePortfolioBlocks() {
  return useQuery({ queryKey: ["portfolio-blocks"], queryFn: getPortfolioBlocks });
}

export function usePortfolioProfiles() {
  return useQuery({ queryKey: ["portfolio-profiles"], queryFn: getPortfolioProfiles });
}

export function usePortfolioCorrelations(windowDays?: number) {
  return useQuery({
    queryKey: ["portfolio-correlations", windowDays],
    queryFn: () => getPortfolioCorrelations(windowDays),
  });
}

export function usePortfolioBenchmark() {
  return useQuery({ queryKey: ["portfolio-benchmark"], queryFn: getPortfolioBenchmark });
}
