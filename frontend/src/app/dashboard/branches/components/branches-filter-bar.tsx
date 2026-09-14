"use client";

import { SearchBar } from "@/components/shared/search-bar";

interface BranchesFilterBarProps {
	searchQuery: string;
	onSearchChange: (value: string) => void;
}

export function BranchesFilterBar({ searchQuery, onSearchChange }: BranchesFilterBarProps) {
	return (
		<div className="flex items-center justify-between gap-4">
			{/* Search */}
			<SearchBar
				containerClassName="max-w-md flex-1"
				iconClassName="left-3 top-1/2 -translate-y-1/2 size-4 text-black-200"
				placeholder="Search for branch..."
				className="pl-9 border-black-50 text-sm h-10 rounded-lg"
				value={searchQuery}
				onChange={(e) => onSearchChange(e.target.value)}
			/>

			{/* Actions */}
			<div className="flex items-center gap-3">
				{/* Add Branch functionality has been moved to CIS Dashboard sync */}
			</div>
		</div>
	);
}
