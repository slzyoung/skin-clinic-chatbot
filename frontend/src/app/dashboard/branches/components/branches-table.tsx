"use client";

import { TableEmptyState } from "@/components/shared/table-empty-state";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { BranchResponse } from "../api/types";
import { BranchesTableRow } from "./branches-table-row";
import { BranchesTableSkeleton } from "./skeletons/branches-table-skeleton";

interface BranchesTableProps {
	branches: BranchResponse[];
	isLoading: boolean;
	hasFilter: boolean;
	isGlobalLimitActive: boolean;
	globalBranchLimit: string;
	onClearFilter: () => void;
}

export function BranchesTable({
	branches,
	isLoading,
	hasFilter,
	isGlobalLimitActive,
	globalBranchLimit,
	onClearFilter,
}: BranchesTableProps) {
	return (
		<div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
			<Table className="[&_tr]:border-gray-100">
				<TableHeader className="bg-gray-50/50">
					<TableRow className="hover:bg-gray-50/50 border-b-gray-100">
						<TableHead className="w-[15%]">Branch Code</TableHead>
						<TableHead className="w-[15%]">Ecosystem</TableHead>
						<TableHead className="w-[25%]">Branch</TableHead>
						<TableHead>Tokens/Month</TableHead>
						<TableHead>Used</TableHead>
						<TableHead>Remaining</TableHead>
						<TableHead className="text-right">Actions</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{isLoading ? (
						<BranchesTableSkeleton rows={5} />
					) : branches.length === 0 ? (
						<TableEmptyState
							colSpan={7}
							title="No branches found"
							description="There are no branches matching your search criteria."
							onClearFilters={hasFilter ? onClearFilter : undefined}
						/>
					) : (
						branches.map((branch) => (
							<BranchesTableRow
								key={branch.id}
								branch={branch}
								isGlobalLimitActive={isGlobalLimitActive}
								globalBranchLimit={globalBranchLimit}
							/>
						))
					)}
				</TableBody>
			</Table>
		</div>
	);
}
