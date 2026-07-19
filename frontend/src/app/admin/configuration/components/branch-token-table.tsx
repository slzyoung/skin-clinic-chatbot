"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { RiSearchLine } from "@remixicon/react";
import { useBranches } from "../hooks/use-branches";
import { AddBranchSheet } from "./add-branch-sheet";
import { ViewBranchSheet } from "./view-branch-sheet";

export function BranchTokenTable() {
	const { data: branches, isLoading } = useBranches();

	return (
		<div className="flex flex-col gap-4 w-full mt-6">
			<div className="flex items-center justify-between gap-4">
				{/* Search */}
				<div className="relative flex-1 max-w-100">
					<RiSearchLine className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-black-200" />
					<Input
						placeholder="Search for branch"
						className="pl-9 bg-white border-black-50 text-sm h-10 rounded-lg"
					/>
				</div>

				{/* Actions */}
				<div className="flex items-center gap-3">
					<AddBranchSheet />
				</div>
			</div>

			<div className="border border-black-50 rounded-md bg-white overflow-hidden">
				<Table>
					<TableHeader>
						<TableRow className="hover:bg-transparent border-b-black-50">
							<TableHead className="w-[30%]">Branch</TableHead>
							<TableHead>Tokens/Month</TableHead>
							<TableHead>Used</TableHead>
							<TableHead>Remaining</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{isLoading ? (
							<TableRow>
								<TableCell colSpan={5} className="text-center py-8 text-gray-500">
									Loading branches...
								</TableCell>
							</TableRow>
						) : branches?.length === 0 ? (
							<TableRow>
								<TableCell colSpan={5} className="text-center py-8 text-gray-500">
									No branches found.
								</TableCell>
							</TableRow>
						) : (
							branches?.map((branch) => (
								<TableRow key={branch.id} className="border-b-black-50">
									<TableCell className="max-w-50">
										<div className="flex items-center gap-3">
											<Avatar className="w-10 h-10 rounded-md after:rounded-md">
												<AvatarImage
													src={branch.image_url || "/mini-placeholder.svg"}
													alt={branch.name}
													className="object-cover rounded-md"
												/>
												<AvatarFallback className="rounded-md">BR</AvatarFallback>
											</Avatar>
											<div className="flex flex-col overflow-hidden">
												<span className="font-medium text-black-500 truncate">{branch.name}</span>
												<span className="text-xs text-black-300 truncate">{branch.address}</span>
											</div>
										</div>
									</TableCell>
									<TableCell className="text-black-500">{branch.tokensMonth}</TableCell>
									<TableCell className="text-black-500">{branch.used}</TableCell>
									<TableCell className="text-black-500">{branch.remaining}</TableCell>
									<TableCell className="text-right">
										<div className="flex justify-end">
											<ViewBranchSheet branch={branch} />
										</div>
									</TableCell>
								</TableRow>
							))
						)}
					</TableBody>
				</Table>
			</div>
		</div>
	);
}
