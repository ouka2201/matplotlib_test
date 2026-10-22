import { Control, Controller, FieldValues, Path } from "react-hook-form";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";

interface Option {
    id: string;
    name: string;
}

interface MasterLocationFieldProps<T extends FieldValues> {
    control: Control<T>;
    prefectureName: Path<T>;
    cityName: Path<T>;
    label: string;
    options: Option[];
    isEditing: boolean;
}

export default function MasterLocationField<T extends FieldValues>({
    control,
    prefectureName,
    cityName,
    label,
    options,
    isEditing,
}: MasterLocationFieldProps<T>) {
    return (
        <FormField
            control={control}
            name={prefectureName}
            render={() => (
                <FormItem className={`flex items-start ${isEditing ? "flex-col gap-1 min-h-[70px]" : "flex-row"}`}>
                    {isEditing ? (
                        <>
                            <div className="flex items-center gap-2 min-h-[24px]">
                                <FormLabel className="text-left input-item-title">{label}</FormLabel>
                            </div>
                            <FormControl className="flex-auto flex w-full min-h-[40px]">
                                <div className="flex gap-2 w-full">
                                    {/* 都道府県 */}
                                    <Controller
                                        name={prefectureName}
                                        control={control}
                                        render={({ field }) => (
                                            <Select
                                                value={field.value || ""}
                                                onValueChange={(val) => field.onChange(val)}
                                                disabled={!isEditing}
                                            >
                                                <SelectTrigger className="w-1/3">
                                                    {options.find((o) => o.id === field.value)?.name || Messages.common.pulldown_default}
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {options.map((opt) => (
                                                        <SelectItem key={opt.id} value={opt.id}>
                                                            {opt.name}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        )}
                                    />

                                    {/* 市区町村 */}
                                    <Controller
                                        name={cityName}
                                        control={control}
                                        render={({ field }) => (
                                            <Input
                                                {...field}
                                                placeholder="市区町村"
                                                disabled={!isEditing}
                                                className="flex-1"
                                            />
                                        )}
                                    />
                                </div>
                            </FormControl>
                            <FormMessage className="text-left" />
                        </>
                    ) : (
                        <div className="flex min-h-[50px] text-base w-full">
                            <div className="flex items-center w-[200px] border border-gray-300 bg-gray-100 text-gray-600 px-3">
                                <span>{label}</span>
                            </div>

                            <div className="flex flex-1 items-center px-3 border-t border-b border-r border-gray-200 text-gray-700">
                                {/* 表示用 */}
                                {`${control._formValues[prefectureName] ?? ""} ${control._formValues[cityName] ?? ""}`}
                            </div>
                        </div>
                    )}
                </FormItem>
            )}
        />
    );
}
