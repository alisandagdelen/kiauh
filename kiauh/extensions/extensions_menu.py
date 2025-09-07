# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import importlib
import inspect
import json
import textwrap
from pathlib import Path
from typing import Dict, List, Type

from core.logger import Logger
from core.menus import Option
from core.menus.base_menu import BaseMenu
from core.types.color import Color
from extensions import EXTENSION_ROOT
from extensions.base_extension import BaseExtension
from utils.input_utils import get_selection_input, get_confirm


# noinspection PyUnusedLocal
# noinspection PyMethodMayBeStatic
class ExtensionsMenu(BaseMenu):
    def __init__(self, previous_menu: Type[BaseMenu] | None = None):
        super().__init__()
        self.title = "Extensions Menu"
        self.title_color = Color.CYAN
        self.previous_menu: Type[BaseMenu] | None = previous_menu
        self.extensions: Dict[str, BaseExtension] = self.discover_extensions()

    def set_previous_menu(self, previous_menu: Type[BaseMenu] | None) -> None:
        from core.menus.main_menu import MainMenu

        self.previous_menu = previous_menu if previous_menu is not None else MainMenu

    def set_options(self) -> None:
        self.options = {
            i: Option(self.extension_submenu, opt_data=self.extensions.get(i))
            for i in self.extensions
        }
        self.options["i"] = Option(self.bulk_install_extensions)

    def discover_extensions(self) -> Dict[str, BaseExtension]:
        ext_dict = {}

        for ext in EXTENSION_ROOT.iterdir():
            metadata_json = Path(ext).joinpath("metadata.json")
            if not metadata_json.exists():
                continue

            try:
                with open(metadata_json, "r") as m:
                    # read extension metadata from json
                    metadata = json.load(m).get("metadata")
                    module_name = metadata.get("module")
                    module_path = f"kiauh.extensions.{ext.name}.{module_name}"

                    # get the class name of the extension
                    module = importlib.import_module(module_path)

                    def predicate(o):
                        return (
                            inspect.isclass(o)
                            and issubclass(o, BaseExtension)
                            and o != BaseExtension
                        )

                    ext_class: type = inspect.getmembers(module, predicate)[0][1]

                    # instantiate the extension with its metadata and add to dict
                    ext_instance: BaseExtension = ext_class(metadata)
                    ext_dict[f"{metadata.get('index')}"] = ext_instance

            except (IOError, json.JSONDecodeError, ImportError) as e:
                print(f"Failed loading extension {ext}: {e}")

        return dict(sorted(ext_dict.items(), key=lambda x: int(x[0])))

    def extension_submenu(self, **kwargs):
        ExtensionSubmenu(kwargs.get("opt_data"), self.__class__).run()

    def bulk_install_extensions(self, **kwargs):
        """Allow user to select multiple extensions for installation"""
        print("\n" + Color.apply("=== Bulk Extension Installation ===", Color.CYAN))
        print("\nAvailable extensions:")
        
        # Display extensions with selection numbers
        for extension in self.extensions.values():
            index = extension.metadata.get("index")
            name = extension.metadata.get("display_name")
            print(f"  {index}) {name}")
        
        print(f"\n{Color.apply('Instructions:', Color.YELLOW)}")
        print("  - Enter extension numbers separated by spaces (e.g., 1 3 5)")
        print("  - Enter 'all' to select all extensions")
        print("  - Enter 'done' when finished selecting")
        
        selected_extensions = []
        
        while True:
            selection = input(Color.apply("Select extensions (or 'done' to proceed): ", Color.CYAN)).strip()
            
            if selection.lower() == 'done':
                break
            elif selection.lower() == 'all':
                selected_extensions = list(self.extensions.values())
                print(f"Selected all {len(selected_extensions)} extensions")
                break
            else:
                # Parse individual selections
                try:
                    indices = selection.split()
                    temp_selected = []
                    for idx in indices:
                        if idx in self.extensions:
                            ext = self.extensions[idx]
                            if ext not in temp_selected:
                                temp_selected.append(ext)
                                print(f"Added: {ext.metadata.get('display_name')}")
                            else:
                                print(f"Already selected: {ext.metadata.get('display_name')}")
                        else:
                            print(f"Invalid extension number: {idx}")
                    
                    if temp_selected:
                        for ext in temp_selected:
                            if ext not in selected_extensions:
                                selected_extensions.append(ext)
                        
                        print(f"\nCurrently selected ({len(selected_extensions)}):")
                        for ext in selected_extensions:
                            print(f"  - {ext.metadata.get('display_name')}")
                
                except Exception as e:
                    print(f"Invalid input format. Please try again.")
        
        if not selected_extensions:
            print("No extensions selected.")
            return
        
        # Confirm installation
        print(f"\n{Color.apply('Selected extensions for installation:', Color.YELLOW)}")
        for ext in selected_extensions:
            print(f"  - {ext.metadata.get('display_name')}")
        
        if get_confirm("Proceed with installation?", True):
            self._install_selected_extensions(selected_extensions)
        else:
            print("Installation cancelled.")

    def _install_selected_extensions(self, extensions: List[BaseExtension]):
        """Install the selected extensions one by one"""
        total = len(extensions)
        successful = 0
        failed = []
        
        print(f"\n{Color.apply('Starting bulk installation...', Color.GREEN)}")
        print(f"Installing {total} extension(s)\n")
        
        for i, extension in enumerate(extensions, 1):
            name = extension.metadata.get('display_name')
            print(f"[{i}/{total}] Installing {name}...")
            
            try:
                extension.install_extension()
                successful += 1
                Logger.print_ok(f"✓ {name} installed successfully")
            except Exception as e:
                failed.append(name)
                Logger.print_error(f"✗ Failed to install {name}: {e}")
            
            print()  # Add spacing between installations
        
        # Installation summary
        print(Color.apply("=== Installation Summary ===", Color.CYAN))
        print(f"Total extensions: {total}")
        print(Color.apply(f"Successful: {successful}", Color.GREEN))
        
        if failed:
            print(Color.apply(f"Failed: {len(failed)}", Color.RED))
            print("Failed extensions:")
            for name in failed:
                print(f"  - {name}")
        else:
            print(Color.apply("All extensions installed successfully! 🎉", Color.GREEN))

    def print_menu(self) -> None:
        line1 = Color.apply("Available Extensions:", Color.YELLOW)
        line2 = Color.apply("I) Bulk Install Extensions", Color.GREEN)
        menu = textwrap.dedent(
            f"""
            ╟───────────────────────────────────────────────────────╢
            ║ {line1:<62} ║
            ║                                                       ║
            """
        )[1:]
        print(menu, end="")

        for extension in self.extensions.values():
            index = extension.metadata.get("index")
            name = extension.metadata.get("display_name")
            row = f"{index}) {name}"
            print(f"║ {row:<53} ║")
        
        print("║                                                       ║")
        print(f"║ {line2:<62} ║")
        print("╟───────────────────────────────────────────────────────╢")


# noinspection PyUnusedLocal
# noinspection PyMethodMayBeStatic
class ExtensionSubmenu(BaseMenu):
    def __init__(
        self, extension: BaseExtension, previous_menu: Type[BaseMenu] | None = None
    ):
        super().__init__()
        self.title = extension.metadata.get("display_name")
        self.title_color = Color.YELLOW
        self.extension = extension
        self.previous_menu: Type[BaseMenu] | None = previous_menu

    def set_previous_menu(self, previous_menu: Type[BaseMenu] | None) -> None:
        self.previous_menu = (
            previous_menu if previous_menu is not None else ExtensionsMenu
        )

    def set_options(self) -> None:
        self.options["1"] = Option(self.extension.install_extension)
        if self.extension.metadata.get("updates"):
            self.options["2"] = Option(self.extension.update_extension)
            self.options["3"] = Option(self.extension.remove_extension)
        else:
            self.options["2"] = Option(self.extension.remove_extension)

    def print_menu(self) -> None:
        line_width = 53
        description: List[str] = self.extension.metadata.get("description", [])
        description_text = Logger.format_content(
            description,
            line_width,
            border_left="║",
            border_right="║",
        )

        menu = textwrap.dedent(
            """
            ╟───────────────────────────────────────────────────────╢
            """
        )[1:]
        menu += f"{description_text}\n"

        # add links if available
        website: str = (self.extension.metadata.get("website") or "").strip()
        repo: str = (self.extension.metadata.get("repo") or "").strip()
        if website or repo:
            links_lines: List[str] = ["Links:"]
            if website:
                links_lines.append(f"● {website}")
            if repo:
                links_lines.append(f"● {repo}")

            links_text = Logger.format_content(
                links_lines,
                line_width,
                border_left="║",
                border_right="║",
            )

            menu += textwrap.dedent(
                """
                ╟───────────────────────────────────────────────────────╢
                """
            )[1:]
            menu += f"{links_text}\n"

        menu += textwrap.dedent(
            """
            ╟───────────────────────────────────────────────────────╢
            ║ 1) Install                                            ║
            """
        )[1:]

        if self.extension.metadata.get("updates"):
            menu += "║ 2) Update                                             ║\n"
            menu += "║ 3) Remove                                             ║\n"
        else:
            menu += "║ 2) Remove                                             ║\n"
        menu += "╟───────────────────────────────────────────────────────╢\n"

        print(menu, end="")
