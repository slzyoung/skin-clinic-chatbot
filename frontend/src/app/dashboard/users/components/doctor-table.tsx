"use client";

import { TableEmptyState } from "@/components/shared/table-empty-state";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { UserResponse } from "../api/types";
import { DoctorTableRow } from "./doctor-table-row";
import { DoctorTableSkeleton } from "./skeletons/doctor-table-skeleton";

interface DoctorTableProps {
	doctors: UserResponse[];
	isLoading: boolean;
	hasFilter: boolean;
	onClearFilter?: () => void;
	onViewDoctor: (doctor: UserResponse) => void;
}

export function DoctorTable({
	doctors,
	isLoading,
	hasFilter,
	onClearFilter,
	onViewDoctor,
}: DoctorTableProps) {
	return (
		<div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
			<Table className="[&_tr]:border-gray-100">
				<TableHeader className="bg-gray-50/50">
					<TableRow>
						<TableHead className="w-[20%]">Name</TableHead>
						<TableHead className="w-[15%]">Employee ID</TableHead>
						<TableHead className="w-[15%]">Dr Type</TableHead>
						<TableHead className="w-[15%]">Branch</TableHead>
						<TableHead className="w-[10%]">Ecosystem</TableHead>
						<TableHead className="w-[20%]">Email</TableHead>
						<TableHead className="w-10 text-right">Actions</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{isLoading ? (
						<DoctorTableSkeleton rows={5} />
					) : doctors.length === 0 ? (
						<TableEmptyState
							colSpan={7}
							title="No doctors found."
							description="There are no doctors matching your search and filter criteria."
							onClearFilters={hasFilter ? onClearFilter : undefined}
						/>
					) : (
						doctors.map((doctor) => (
							<DoctorTableRow key={doctor.id} doctor={doctor} onView={onViewDoctor} />
						))
					)}
				</TableBody>
			</Table>
		</div>
	);
}
