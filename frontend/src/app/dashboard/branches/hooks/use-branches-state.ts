"use client";

import { useConfigs } from "@/app/dashboard/configuration/hooks/use-config";
import { useDebounce } from "@/hooks/use-debounce";
import { usePagination } from "@/hooks/use-pagination";
import { useMemo, useState } from "react";
import { BranchResponse } from "../api/types";
import { useBranches } from "./use-branches";

export function useBranchesState() {
	const [searchQuery, setSearchQuery] = useState("");
	const debouncedSearch = useDebounce(searchQuery, 300);

	const { data: branches = [], isLoading } = useBranches();
	const { data: configs } = useConfigs();

	const isGlobalLimitActive =
		configs?.find((c) => c.key === "GLOBAL_TOKEN_LIMIT_ACTIVE")?.value === "true";
	const globalBranchLimit =
		configs?.find((c) => c.key === "GLOBAL_TOKEN_LIMIT")?.value || "3000000";

	const filteredBranches = useMemo(() => {
		if (!branches) return [];
		if (!debouncedSearch.trim()) return branches;
		const q = debouncedSearch.toLowerCase();
		return branches.filter(
			(branch) =>
				branch.name?.toLowerCase().includes(q) ||
				branch.code?.toLowerCase().includes(q) ||
				branch.ecosystem?.toLowerCase().includes(q),
		);
	}, [branches, debouncedSearch]);

	const pagination = usePagination<BranchResponse>({
		items: filteredBranches,
		initialPageSize: 10,
	});

	const handleClearSearch = () => {
		setSearchQuery("");
	};

	return {
		searchQuery,
		setSearchQuery,
		handleClearSearch,
		isLoading,
		hasFilter: Boolean(debouncedSearch.trim()),
		isGlobalLimitActive,
		globalBranchLimit,
		filteredBranches,
		pagination,
	};
}
