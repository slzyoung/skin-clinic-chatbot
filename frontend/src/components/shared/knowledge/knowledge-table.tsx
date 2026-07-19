"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import {
	RiArrowDownSLine,
	RiDatabase2Line,
	RiEyeLine,
	RiLoader4Line,
	RiMoneyDollarCircleLine,
	RiSearchLine,
} from "@remixicon/react";
import { useKnowledgeBaseList } from "../../../app/admin/knowledge/hooks/use-knowledge";

export function KnowledgeTable({ type = "PRODUCT" }: { type?: string }) {
	const { data: knowledgeList, isLoading, isError } = useKnowledgeBaseList(type);
	return (
		<div className="w-full mt-6">
			{/* Filters */}
			<div className="flex items-center justify-between mb-4">
				<div className="relative flex items-center w-full max-w-sm">
					<RiSearchLine className="absolute left-2.5 w-4 h-4 text-gray-400" />
					<Input placeholder="Search for product name" className="pl-8 bg-white" />
				</div>
				<div className="flex items-center gap-3">
					<Button variant="outline" className="gap-2 bg-white hover:bg-gray-50 text-gray-700">
						<RiDatabase2Line className="w-4 h-4" />
						Filter by category
						<RiArrowDownSLine className="w-4 h-4 text-gray-400" />
					</Button>
					<Button variant="outline" className="gap-2 bg-white hover:bg-gray-50 text-gray-700">
						<RiMoneyDollarCircleLine className="w-4 h-4" />
						Filter by price
						<RiArrowDownSLine className="w-4 h-4 text-gray-400" />
					</Button>
				</div>
			</div>

			{/* Table */}
			<div className="border border-gray-100 rounded-md bg-white overflow-hidden">
				<Table className="[&_tr]:border-gray-100">
					<TableHeader className="bg-gray-50/50">
						<TableRow className="bg-gray-50/50 hover:bg-gray-50/50">
							<TableHead className="w-62.5 font-medium text-gray-700">Knowledge Title</TableHead>
							<TableHead className="w-37.5 font-medium text-gray-700">Category</TableHead>
							<TableHead className="font-medium text-gray-700">Description</TableHead>
							<TableHead className="w-30 font-medium text-gray-700">Status</TableHead>
							<TableHead className="w-30 font-medium text-gray-700 text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{isLoading && (
							<TableRow>
								<TableCell colSpan={5} className="text-center py-8 text-gray-500">
									<div className="flex items-center justify-center">
										<RiLoader4Line className="w-5 h-5 animate-spin mr-2" />
										Loading knowledge base...
									</div>
								</TableCell>
							</TableRow>
						)}

						{isError && (
							<TableRow>
								<TableCell colSpan={5} className="text-center py-8 text-red-500">
									Failed to load knowledge base documents.
								</TableCell>
							</TableRow>
						)}

						{!isLoading && !isError && knowledgeList?.length === 0 && (
							<TableRow>
								<TableCell colSpan={5} className="text-center py-8 text-gray-500">
									No knowledge base documents found.
								</TableCell>
							</TableRow>
						)}

						{!isLoading &&
							knowledgeList?.map((row) => (
								<TableRow key={row.id}>
									<TableCell>
										<div className="flex items-center gap-3">
											<Avatar className="w-10 h-10 rounded-md after:rounded-md">
												<AvatarImage
													src="/mini-placeholder.svg"
													alt={row.title}
													className="object-cover rounded-md"
												/>
												<AvatarFallback className="rounded-md">KB</AvatarFallback>
											</Avatar>
											<div className="flex flex-col">
												<span className="font-medium text-gray-900 line-clamp-1">{row.title}</span>
												<span className="text-xs text-gray-500">{row.file_name}</span>
											</div>
										</div>
									</TableCell>
									<TableCell>
										<Badge
											variant="secondary"
											className="bg-gray-100 text-gray-700 hover:bg-gray-100"
										>
											{row.type}
										</Badge>
									</TableCell>
									<TableCell>
										<p className="text-sm text-gray-600 line-clamp-2 max-w-md">
											{row.ai_summary || row.content || "No description available."}
										</p>
									</TableCell>
									<TableCell>
										<Badge
											variant="secondary"
											className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50 border-emerald-100/50"
										>
											{row.status}
										</Badge>
									</TableCell>
									<TableCell className="text-right">
										<div className="flex justify-end gap-2">
											<Button variant="outline" size="md" className="border-gray-200 font-medium">
												<RiEyeLine className="mr-2 h-4 w-4" />
												View
											</Button>
										</div>
									</TableCell>
								</TableRow>
							))}
					</TableBody>
				</Table>
			</div>
		</div>
	);
}
