import sys

def assure_newlines(lst): # make sure all entries in the array of lines has a newline character at the end
    newlst = []
    for entry in lst:
        if entry.find("\n") == -1: #if no newline
            newlst.append(entry + "\n")
            continue
        newlst.append(entry)
    return newlst


def align_and_strip(inputlst): # specifically for when nyx put ATTACK args in a vertical line lul (and also deletes whitespace at beginning of lines)
    lst = []
    for _ in inputlst: # 0-noninclusive
        if _ != "\n": # check for blank lines
            line = _.strip() # deletes whitespace to left of first character in string
            if line.find("/*") <= 1 and line.find("/*") != -1: # find returns -1 if string doesn't exist
                lst[len(lst)-1] += line
                continue
            lst.append(line)

    return lst




def format_to_skyline_acmd(oldlst):
    lst = []
    replaceTexts = [
        ["acmd->", ""],
        ["is_excute()", "is_execute"],
        ["game_CaptureCutCommon(acmd)", "game_CaptureCutCommon()"],
        ["module_accessor,", ""],
        ["module_accessor", ""],
        ["0x1", "true"],
        ["0x0", "false"]
    ]

    for line in oldlst:
        newline = line
        for x in replaceTexts:
            newline = newline.replace(x[0], x[1])


        #   adding LUA_VOID args to ATTACK funcs that don't have X2/Y2/Z2  (assumed if X2 is present, the rest are also)
        if "ATTACK" in newline and "X2" not in newline: # doesn't have X2/Y2/Z2 args - needs LUA_VOID's
            newline = newline.replace(" /*Hitlag*/", " /*X2*/ LUA_VOID, /*Y2*/ LUA_VOID, /*Z2*/ LUA_VOID, /*Hitlag*/")


        #   Fix acmd->wrap's
        if "wrap" in newline:
            wrapped_func_name = newline[newline.find("(")+1:newline.find(",")]
            args_arr = newline[newline.find("L2CValue("):].replace("});", "").split(",")
            newarr = []
            for element in args_arr:
                stripped = element.strip()
                if "hash40" not in stripped:
                    arg = stripped[stripped.find("(")+1:stripped.find(")")]
                elif "hash40" in stripped: # special case for hash40's since they have ()
                    arg = stripped[stripped.find("(")+1:stripped.find('")')+2]
                newarr.append(arg)
            newline = wrapped_func_name + "(" + ", ".join(newarr) + ")"


        # now that wraps are fixed - we gotta fix wrap function namespace stuff (I.E. sv_module_access or any other sv_ namespaces)
        if "grab" in newline:
            newline = newline.replace("grab(MA_MSC_CMD_GRAB_CLEAR_ALL)", "sv_module_access::grab(MA_MSC_CMD_GRAB_CLEAR_ALL)")

        # increment frame declarations
        if "frame(" in newline:
            frame = int(newline[newline.find("(")+1:newline.find(")")]) + 1 # <- increment here
            newline = "frame(" + str(frame) + ")"

        lst.append(newline)
    return lst




def format_skyline_acmd_header(oldlst):
    lst = oldlst


    for linenum in range(len(oldlst)): #        Take out blank/non-acmd lines at the beginning of the txt file - ensures that the ACMD header will be the first line
        if oldlst[linenum].find("ACMD") != -1: #  this is case-sensitive
            lst = oldlst[linenum:]
            break



    #   Format ACMD header into new skyline function

    old_acmd_header = lst[0] # since first line will be the ACMD header - we store it for later here

    if "[]" not in old_acmd_header: # if the rest of the acmd header is not in the same line, we take out first 2 lines, otherwise, just the first line
        lst = lst[2:]
    else:
        lst = lst[1:]
    lst = ["});\n}" if line == "})," else line for line in lst] # account for acmd!({ and for end of function {

    # parse old Salty acmd header for relevant info ---         IF FOR SOME REASON YOU WANNA CHANGE THIS - use .split(",") which will split the string into a list seperated by the specified delimiter

        # battle_object_kind
    battle_object_kind_start_idx = old_acmd_header.find("FIGHTER_KIND_")
    battle_object_kind_end_idx = old_acmd_header.find('",', battle_object_kind_start_idx)
    battle_object_kind = old_acmd_header[battle_object_kind_start_idx:battle_object_kind_end_idx]


        # animation
    animation_start_idx = battle_object_kind_end_idx + 3    # gets us to the first " of the animation name - since slices are [inclusive:exclusive]
    animation_end_idx = old_acmd_header.find(",", animation_start_idx) # gets us the comma after the anim name - since end of slice is exclusive
    animation = old_acmd_header[animation_start_idx:animation_end_idx] # animation name with " "

        # animcmd
    animcmd_start_idx = animation_end_idx + 2
    animcmd_end_idx = old_acmd_header.find(",", animcmd_start_idx)
    animcmd = old_acmd_header[animcmd_start_idx:animcmd_end_idx]


    # will hold newly formatted skyline acmd header/function sig - since salty couldn't do weapon acmd anyway, I assume its always BATTLE_OBJECT_CATEGORY_FIGHTER
    new_acmd_header = "\n\n#[acmd::acmd_func(\nbattle_object_category = BATTLE_OBJECT_CATEGORY_FIGHTER,\n" + "battle_object_kind = " + battle_object_kind + ",\n" + "animation = " + animation + ",\n" + "animcmd = " + animcmd + "\n)]\n"

    #                         since its always fighter_kind_
    new_acmd_func_sig = "fn " + battle_object_kind[13:].lower() + "_" + animation[1:len(animation)-1] + "_" + animcmd[1:animcmd.find("_")] + "(fighter: &mut L2CFighterCommon) {\nacmd!({\n"


    lst.insert(0, new_acmd_func_sig) # prepend new function signature
    lst.insert(0, new_acmd_header) # prepend new header now before the func sig

    return lst


def convert_acmd(lst):
    return assure_newlines(format_skyline_acmd_header(format_to_skyline_acmd(align_and_strip(lst))))


def main():
    filename = sys.argv[1]
    file = open(filename, "r")
    lines = file.readlines()
    file.close()

    # batch ACMD convert - also inherently supports single ACMD obj conversion
    finallst = []
    for line_num in range(len(lines)):
        if "ACMD(" in lines[line_num]: # beginning of ACMD obj
            obj_beginning = line_num
        elif "})," in lines[line_num]: # end of ACMD obj
            obj_end = line_num
            finallst.append(convert_acmd(lines[obj_beginning:obj_end+1])) # convert and append the ACMD obj when an "end" is detected, then move on


    newfile = open("ConvertedACMD.txt", "w")
    for lst in finallst:
        newfile.writelines(lst)
    newfile.close()

main()