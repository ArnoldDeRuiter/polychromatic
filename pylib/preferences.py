#!/usr/bin/env python3
#
# Polychromatic is licensed under the GPLv3.
# Copyright (C) 2015-2019 Luke Horwell <code@horwell.me>
#
"""
This module is responsible for loading/saving persistent data used by Polychromatic's frontends.
"""

import os
import json
import shutil
import time
from . import common

version = 6
verbose = False

dbg = common.Debugging()


class Paths(object):
    # Directories
    root = os.path.join(os.path.expanduser("~"), ".config", "polychromatic")
    profile_folder = os.path.join(root, "profiles")
    profile_backups = os.path.join(root, "backups")
    cache = os.path.join(os.path.expanduser("~"), ".cache", "polychromatic")
    effects = os.path.join(root, "effects")

    # Files
    preferences = os.path.join(root, "preferences.json")
    devicestate = os.path.join(root, "devicestate.json")
    colours     = os.path.join(root, "colours.json")

    # Deprecated
    old_profiles = os.path.join(root, "profiles.json")

    # Data Source
    @staticmethod
    def get_data_source(program_path):
        if os.path.exists(os.path.abspath(os.path.join(os.path.dirname(program_path), "data/"))):
            path = os.path.abspath(os.path.join(os.path.dirname(program_path), "data/"))
        elif os.path.exists("/usr/share/polychromatic/"):
            path = "/usr/share/polychromatic/"
        else:
            dbg.stdout("Data directory cannot be located. Exiting.", dbg.error)
            exit(1)
        return path


################################################################################
def load_file(filepath, no_version_check=False):
    """
    Loads a save file from disk.
    """
    # Does it exist?
    if os.path.exists(filepath):
        # Load data into memory.
        try:
            with open(filepath) as stream:
                data = json.load(stream)
        except Exception as e:
            dbg.stdout("Failed to load '{0}'.\nException: {1}".format(filepath, str(e)), dbg.error)
            init_config(filepath)
            data = {}
    else:
        init_config(filepath)
        data = {}
        no_version_check = True

    # Check configuration version if reading the preferences.
    if filepath == path.preferences and no_version_check == False:
        try:
            config_version = int(data["config_version"])
        except KeyError:
            data["config_version"] = version
            config_version = version

        # Is the software newer and the configuration old?
        if version > config_version:
            upgrade_old_pref(config_version)

        # Is the config newer then the software? Wicked time travelling!
        if config_version > version:
            dbg.stdout("\nWARNING: Your preferences file is newer then the module!", dbg.error)
            dbg.stdout("This could cause undesired glitches in applications. Consider updating the Python modules.", dbg.error)
            dbg.stdout("    Your Config Version:     v." + str(config_version), dbg.error)
            dbg.stdout("     Software Config Version: v." + str(version), dbg.error)
            dbg.stdout("")

    # Passes data back to the variable
    return(data)


def save_file(filepath, newdata):
    """
    Commit the save file to disk.
    """

    # Write configuration version if the preferences.
    if filepath == path.preferences:
        newdata["config_version"] = version

    # Create file if it doesn"t exist.
    if not os.path.exists(filepath):
        open(filepath, "w").close()

    # Write new data to specified file.
    if os.access(filepath, os.W_OK):
        f = open(filepath, "w+")
        f.write(json.dumps(newdata, sort_keys=True, indent=4))
        f.close()
    else:
        dbg.stdout("Cannot write to file: " + filepath, dbg.error)


def set(group, setting, value, filepath=None):
    """
    Commits a new preference value, then saves it to disk.
    A different file can be optionally specified.
    """
    # Example: ("editor", "live_preview", True)
    #          ("24", "name", "Test Program", "/path/to/profiles.json")

    # If haven't explicitly stated which file, assume preferences.
    if filepath == None:
        filepath = path.preferences

    data = load_file(filepath)

    # In case a boolean was passed via JavaScript, correct the data type.
    if value == "true":
        value = True
    if value == "false":
        value = False

    # Create group if non-existent.
    try:
        data[group]
    except:
        data[group] = {}

    # Write new setting and save.
    try:
        data[group][setting] = value
        save_file(filepath, data)
    except:
        dbg.stdout("Failed to write '{0}' for item '{1}' in group '{2}'!".format(value, setting, group), dbg.error)


def get(group, setting, default_value="", filepath=None):
    """
    Read data from memory.
    """
    # Example: ("editor", "live_preview", "True")
    #          ("12", "name", "Unknown", "/path/to/profiles.json")

    # If no file explicitly stated, assume preferences.
    if filepath == None:
        filepath = path.preferences

    data = load_file(filepath)

    # Read data from preferences.
    try:
        value = data[group][setting]
        return value
    except:
        # Should it be non-existent, return a fallback option.
        if verbose:
            dbg.stdout("Preference '{0}' in '{1}' non-existent. Using default '{2}' instead.".format(setting, group, default_value), dbg.debug)
        set(group, setting, default_value, filepath)
        return default_value


def exists(group, setting, filepath=None):
    """
    Returns a boolean whether preference exists or not.
    """

    # If no file explicitly stated, assume preferences.
    if filepath == None:
        filepath = path.preferences

    data = load_file(filepath)

    # Read data from preferences.
    try:
        value = data[group][setting]
        return True
    except:
        return False


def get_group(group, filepath):
    """
    Read a group of data as a list.
    """
    # Must explictly state the file path, and the group (or "root")
    data = load_file(filepath)

    try:
        if group == 'root':
            listdata = list(data.keys())
        else:
            listdata = list(data[group].keys())
    except:
        dbg.stdout("Failed to retrieve data from group '{0]' from file '{1}'".format(group, os.path.basename(filepath)), dbg.error)
        return []

    return listdata


def init_config(filepath):
    """
    Prepares a configuration file for the first time.
    """
    try:
        # Backup if the JSON was invalid.
        if os.path.exists(filepath):
            dbg.stdout("JSON corrupt and will be backed up then discarded: " + filepath, dbg.error)
            os.rename(filepath, filepath + ".bak")

        # Touch new file
        save_file(filepath, {})
        if verbose:
            dbg.stdout("New configuration ready: " + filepath, dbg.success)

    except Exception as e:
        # Couldn't create the default configuration.
        dbg.stdout("Failed to write default preferences.", dbg.error)
        dbg.stdout("Exception: ", str(e), dbg.error)


def clear_config():
    """
    Erases all the configuration stored on disk.
    """
    if verbose:
        dbg.stdout("Deleting configuration folder '" + path.root + "'...", dbg.action)
    shutil.rmtree(path.root)


def reset_config(filepath):
    """
    Resets a specific configuration file stored on disk.
    This will cause it to be re-generated when it is next called.
    """
    if verbose:
        dbg.stdout("Resetting configuration file: " + filepath, dbg.action)
    os.remove(filepath)
    start_initalization()


def upgrade_old_pref(config_version):
    """
    Updates the configuration from previous revisions.
    """
    dbg.stdout("Upgrading configuration from v{0} to v{1}...".format(config_version, version), dbg.action)

    if config_version < 3:
        # *** "chroma_editor" group now "editor" ***
        data = load_file(path.preferences, True)
        data["editor"] = data["chroma_editor"]
        data.pop("chroma_editor")
        save_file(path.preferences, data)

        # *** Profiles now indexed, not based on file names. ***
        import time
        index = {}
        for profile in os.listdir(path.profile_folder):
            uid = int(time.time() * 1000000)
            old = os.path.join(path.profile_folder, profile)
            new = os.path.join(path.profile_folder, str(uid))
            os.rename(old, new)
            index[str(uid)] = {}
            index[str(uid)]["name"] = profile
        save_file(path.old_profiles, index)

        # *** Clear backups ***
        shutil.rmtree(path.profile_backups)
        os.mkdir(path.profile_backups)

    if config_version < 4:
        # *** Convert old serialised profile binary to JSON ***
        # Thanks to @terrycain for providing the conversion code.

        # Backup the old serialised versions, although they're useless now.
        if not os.path.exists(path.profile_backups):
            os.mkdir(path.profile_backups)

        # Load profiles and old index (meta data will now be part of that file)
        profiles = os.listdir(path.profile_folder)
        index = load_file(path.old_profiles, True)

        # Import daemon class required for conversion.
        from razer_daemon.keyboard import KeyboardColour

        for filename in profiles:
            # Get paths and backup.
            backup_path = os.path.join(path.profile_backups, filename)
            old_path = os.path.join(path.profile_folder, filename)
            new_path = os.path.join(path.profile_folder, filename + '.json')
            os.rename(old_path, backup_path)

            # Open the serialised format and export to JSON instead.
            blob = open(backup_path, 'rb').read()
            rgb_profile_object = KeyboardColour()
            rgb_profile_object.get_from_total_binary(blob)

            json_structure = {'rows':{}}
            for row_id, row in enumerate(rgb_profile_object.rows):
                row_id = str(row_id) # JSON doesn't like numbered keys
                json_structure['rows'][row_id] = [rgb.get() for rgb in row]

            # Migrate index meta data, and save.
            uuid = os.path.basename(old_path)
            json_structure["name"] = index[uuid]["name"]
            json_structure["icon"] = index[uuid]["icon"]
            save_file(new_path, json_structure)

        # Delete index file as no longer needed.
        os.remove(path.old_profiles)

    if config_version < 5:
        # Ensure preferences.json is clean.
        data = load_file(path.preferences, True)
        for key in ["activate_on_save", "live_switch", "live_preview"]:
            try:
                value = data["editor"][key]
                if type(value) == str:
                    if value in ['true', 'True']:
                        data["editor"][key] = True
                    else:
                        data["editor"][key] = False
            except Exception:
                pass

        save_file(path.preferences, data)

    if config_version < 6:
        # Migrate preferences.json to new keys
        old_data = load_file(path.preferences, True)
        try:
            old_live_preview = old_data["editor"]["live_preview"]
            old_tray_type = old_data["tray_icon"]["type"]
            old_tray_value = old_data["tray_icon"]["value"]
        except KeyError:
            old_live_preview = ""
            old_tray_type = ""
            old_tray_value = ""

        new_data = {
            "colours": {
                "primary": "#00FF00",
                "secondary": "#00FFFF"
            },
            "effects": {
                "live_preview": old_live_preview
            },
            "tray_icon": {
                "force_fallback": False
            }
        }

        if old_tray_type == "builtin":
            new_data["tray_icon"]["icon_id"] = old_tray_value
        elif old_tray_type == "gtk":
            new_data["tray_icon"]["gtk_icon_name"] = old_tray_value
        elif old_tray_type == "custom":
            new_data["tray_icon"]["custom_image_path"] = old_tray_value

        save_file(path.preferences, new_data)

        # Migrate colours from RGB lists to HEX strings.
        # -- Saved Colours
        new_colours = []
        old_colours = load_file(path.colours)
        old_ids = list(old_colours.keys())
        old_ids.sort()
        for uuid in old_ids:
            try:
                new_name = old_colours[uuid]["name"]
                new_hex = common.rgb_to_hex(old_colours[uuid]["col"])
                new_colours.append({"name": new_name, "hex": new_hex})
            except Exception:
                # Ignore invalid data
                pass

        save_file(path.colours, new_colours)

        # -- Device State
        data = load_file(path.devicestate, True)
        for serial in data.keys():
            for source in data[serial].keys():
                for key in ["colour_primary", "colour_secondary"]:
                    try:
                        rgb = data[serial][source][key]
                        new_hex = common.rgb_to_hex(rgb)
                        data[serial][source][key] = new_hex
                    except Exception as e:
                        # Key non-existant
                        pass
        save_file(path.devicestate, data)

    # Write new version number.
    pref_data = load_file(path.preferences, True)
    pref_data["config_version"] = version
    save_file(path.preferences, pref_data)

    dbg.stdout("Configuration successfully upgraded.", dbg.success)


def set_device_state(serial, source, state, value):
    """
    Checks the devicestate file for the status on a device.
        serial  = Serial number or unique identifer of the device.
        source  = Light source to check, e.g. "main", "logo", "scroll".
        state   = Name of state, e.g. "brightness", "effect", "colour_primary", etc.
    """
    data = load_file(path.devicestate, True)

    try:
        data[serial]
    except KeyError:
        data[serial] = {}

    try:
        data[serial][source]
    except KeyError:
        data[serial][source] = {}

    data[serial][source][state] = value
    save_file(path.devicestate, data)
    if verbose:
        dbg.stdout("Set device state: [Serial: {0}] [Source: {1}] [State: {2}] [Value: {3}]".format(serial, source, state, value), dbg.debug)


def get_device_state(serial, source, state):
    """
    Reads the device state file for a specific state.
        serial  = Serial number or unique identifer of the device.
        source  = Light source to check, e.g. "main", "logo", "scroll".
        state   = Name of state, e.g. "effect", "effect_params", "colour_primary", etc.
    """
    data = load_file(path.devicestate, True)

    try:
        value = data[serial][source][state]
        return value
        if verbose:
            dbg.stdout("Device state recalled: [Serial: {0}] [Source: {1}] [State: {2}] [Value: {3}]".format(serial, source, state, value), dbg.debug)
    except KeyError:
        if verbose:
            dbg.stdout("Device state recalled: [Serial: {0}] [Source: {1}] [State: {2}] [No value]".format(serial, source, state), dbg.debug)
        return None
    except TypeError:
        dbg.stdout("Device state corrupt:  [Serial: {0}] [Source: {1}] ... Will reset.".format(str(serial), str(source)), dbg.debug)
        data.pop(serial)
        save_file(path.devicestate, data)
        return None


def generate_uuid():
    """
    Returns a random UUID.
    """
    return(str(int(time.time() * 1000000)))


# Module Initalization
def start_initalization():
    """
    Prepares the preferences module for use.
    """
    # Create folders if they do not exist.
    for folder in [path.root, path.effects, path.profiles, path.cache]:
        if not os.path.exists(folder):
            if verbose:
                dbg.stdout("Configuration folder does not exist. Creating: ", folder, dbg.action)
            os.makedirs(folder)

    # Create preferences if non-existent.
    for json_path in [path.preferences]:
        if not os.path.exists(json_path):
            init_config(json_path)

    # Populate with defaults if none exists.
    ## Default Preferences
    data = load_file(path.preferences, True)
    if len(data) <= 2:
        default_pref = {
            "editor": {
                "live_switch": True,
                "scaling": 1,
                "live_preview": True,
                "activate_on_save": True
            },
            "tray_icon": {
                "type": "builtin",
                "value": "0"
            }
        }
        save_file(path.preferences, default_pref)

    ## Default Colours
    data = load_file(path.colours, True)
    if len(data) <= 2:
        default_data = [
            {"name": _("White"), "hex": "#FFFFFF"},
            {"name": _("Red"), "hex": "#FF0000"},
            {"name": _("Green"), "hex": "#00FF00"},
            {"name": _("Blue"), "hex": "#0000FF"},
            {"name": _("Aqua"), "hex": "#00FFFF"},
            {"name": _("Orange"), "hex": "#FFA500"},
            {"name": _("Pink"), "hex": "#FFC0CB"},
            {"name": _("Purple"), "hex": "#800080"},
            {"name": _("Yellow"), "hex": "#FFFF00"},
            {"name": _("Light Grey"), "hex": "#BFBFBF"},
            {"name": _("Dark Grey"), "hex": "#7F7F7F"}
        ]
        save_file(path.colours, default_data)

_ = common.setup_translations(__file__, "polychromatic")
path = Paths()
start_initalization()
