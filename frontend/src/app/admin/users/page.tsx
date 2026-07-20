"use client";

import { RiEyeLine, RiSearchLine, RiAddLine, RiRefreshLine } from "@remixicon/react";
import { useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { DoctorDetailsSheet } from "./components/doctor-details-sheet";
import { UserAddSheet } from "./components/user-add-sheet";
import { UserStaffProfileSheet } from "./components/user-staff-profile-sheet";
import { useUsers } from "./hooks/use-users";
import { useSyncCIS } from "./hooks/use-sync";
import { UserResponse } from "./api/types";

export default function UsersPage() {
	const { data: staffData = [] } = useUsers("STAFF");
	const { data: doctorData = [] } = useUsers("DOCTOR");
	const syncCIS = useSyncCIS();

	const [selectedDoctor, setSelectedDoctor] = useState<UserResponse | null>(null);
	const [isSheetOpen, setIsSheetOpen] = useState(false);

	const [isAddUserOpen, setIsAddUserOpen] = useState(false);
	const [selectedStaff, setSelectedStaff] = useState<UserResponse | null>(null);
	const [isViewStaffOpen, setIsViewStaffOpen] = useState(false);

	const handleViewDoctor = (doctor: UserResponse) => {
		setSelectedDoctor(doctor);
		setIsSheetOpen(true);
	};

	const handleViewStaff = (staff: UserResponse) => {
		setSelectedStaff(staff);
		setIsViewStaffOpen(true);
	};

	const selectedDoctorLive = doctorData.find((d) => d.id === selectedDoctor?.id) || selectedDoctor;
	const selectedStaffLive = staffData.find((s) => s.id === selectedStaff?.id) || selectedStaff;

	return (
		<div className="flex flex-col h-full gap-6 p-6">
			<div className="flex flex-col gap-1">
				<h1 className="text-xl font-semibold text-foreground">User</h1>
				<p className="text-sm text-muted-foreground">
					Easily handle user accounts without any hassle.
				</p>
			</div>

			<Tabs defaultValue="staff" className="w-full">
				<TabsList variant="line" className="mb-6">
					<TabsTrigger
						value="staff"
						className="font-medium text-sm text-gray-500 hover:text-blue-500 data-active:text-blue-500 data-active:after:bg-blue-500"
					>
						Staff
					</TabsTrigger>
					<TabsTrigger
						value="doctors"
						className="font-medium text-sm text-gray-500 hover:text-blue-500 data-active:text-blue-500 data-active:after:bg-blue-500"
					>
						Doctor
					</TabsTrigger>
				</TabsList>

				<div className="flex items-center justify-between mb-4">
					<div className="relative flex items-center w-full max-w-100">
						<RiSearchLine className="absolute left-2.5 w-4 h-4 text-gray-400" />
						<Input placeholder="Search for user, staff, or doctor" className="pl-8 bg-white" />
					</div>
					<div className="flex items-center gap-2">
						<Button
							variant="outline"
							className="bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:text-gray-900"
							onClick={() => syncCIS.mutate()}
							disabled={syncCIS.isPending}
						>
							<RiRefreshLine
								className={`mr-2 h-4 w-4 ${syncCIS.isPending ? "animate-spin" : ""}`}
							/>
							{syncCIS.isPending ? "Syncing..." : "Sync with CIS"}
						</Button>
						<Button
							className="bg-blue-600 hover:bg-blue-700"
							onClick={() => setIsAddUserOpen(true)}
						>
							<RiAddLine className="mr-2 h-4 w-4" />
							Add New User
						</Button>
					</div>
				</div>

				<TabsContent value="staff" className="mt-0 outline-none">
					<div className="border border-gray-100 rounded-md bg-white overflow-hidden">
						<Table className="[&_tr]:border-gray-100">
							<TableHeader className="bg-gray-50/50">
								<TableRow>
									<TableHead className="w-[35%]">Name</TableHead>
									<TableHead className="w-[20%]">Role</TableHead>
									<TableHead>Email</TableHead>
									<TableHead className="w-30 text-right">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{staffData.map((staff: UserResponse) => (
									<TableRow key={staff.id}>
										<TableCell>
											<div className="flex items-center gap-3">
												<Avatar className="h-10 w-10">
													<AvatarFallback className="bg-gray-100 text-gray-600 font-medium">
														{staff.name
															? staff.name
																	.split(" ")
																	.map((n: string) => n[0])
																	.join("")
															: "S"}
													</AvatarFallback>
												</Avatar>
												<div className="flex flex-col">
													<span className="font-medium text-sm text-gray-900">{staff.name}</span>
												</div>
											</div>
										</TableCell>
										<TableCell className="text-gray-900">
											{staff.roles && staff.roles.length > 0 ? staff.roles[0].name : "Staff"}
										</TableCell>
										<TableCell className="text-gray-900">{staff.email}</TableCell>
										<TableCell className="text-right">
											<div className="flex justify-end gap-2">
												<Button
													variant="outline"
													size="md"
													className="border-gray-200 font-medium"
													onClick={() => handleViewStaff(staff)}
												>
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
				</TabsContent>

				<TabsContent value="doctors" className="mt-0 outline-none">
					<div className="border border-gray-100 rounded-md bg-white overflow-hidden">
						<Table className="[&_tr]:border-gray-100">
							<TableHeader className="bg-gray-50/50">
								<TableRow>
									<TableHead className="w-[30%]">Name</TableHead>
									<TableHead className="w-[15%]">Role</TableHead>
									<TableHead className="w-[20%]">Email</TableHead>
									<TableHead className="w-[15%]">Tokens</TableHead>
									<TableHead className="w-20 text-right">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{doctorData.map((doc: UserResponse) => (
									<TableRow key={doc.id}>
										<TableCell>
											<div className="flex items-center gap-3">
												<Avatar className="h-10 w-10">
													<AvatarFallback className="bg-gray-100 text-gray-600 font-medium">
														{doc.name
															? doc.name
																	.replace("Dr. ", "")
																	.split(" ")
																	.map((n: string) => n[0])
																	.join("")
															: "D"}
													</AvatarFallback>
												</Avatar>
												<div className="flex flex-col">
													<span className="font-medium text-sm text-gray-900">{doc.name}</span>
												</div>
											</div>
										</TableCell>
										<TableCell className="text-gray-900">Doctor</TableCell>
										<TableCell className="text-gray-900">{doc.email}</TableCell>
										<TableCell>
											<div className="flex flex-col gap-1">
												<span className="text-sm font-medium text-gray-900">
													{doc.tokens_used ?? 0} / {doc.token_limit ?? 0}
												</span>
												<div className="w-full bg-gray-200 rounded-full h-1.5">
													<div
														className="bg-blue-600 h-1.5 rounded-full"
														style={{
															width: `${Math.min(((doc.tokens_used ?? 0) / (doc.token_limit ?? 1)) * 100, 100)}%`,
														}}
													></div>
												</div>
											</div>
										</TableCell>
										<TableCell className="text-right">
											<div className="flex justify-end gap-2">
												<Button
													variant="outline"
													size="md"
													className="border-gray-200 font-medium"
													onClick={() => handleViewDoctor(doc)}
												>
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
				</TabsContent>
			</Tabs>

			<DoctorDetailsSheet
				isOpen={isSheetOpen}
				onOpenChange={setIsSheetOpen}
				doctor={selectedDoctorLive}
			/>

			<UserAddSheet isOpen={isAddUserOpen} onOpenChange={setIsAddUserOpen} />

			<UserStaffProfileSheet
				isOpen={isViewStaffOpen}
				onOpenChange={setIsViewStaffOpen}
				staff={selectedStaffLive}
			/>
		</div>
	);
}
