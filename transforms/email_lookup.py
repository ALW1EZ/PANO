from dataclasses import dataclass
from typing import ClassVar, List, Dict, Any
import httpx
from datetime import datetime
from dateutil.relativedelta import relativedelta

from .base import Transform
from entities.base import Entity
from entities.email import Email
from entities.username import Username
from entities.website import Website
from entities.image import Image
from entities.location import Location
from entities.event import Event
from ui.managers.status_manager import StatusManager

from ghunt import globals as gb
from ghunt.helpers.utils import get_httpx_client
from ghunt.objects.base import GHuntCreds
from ghunt.apis.peoplepa import PeoplePaHttp
from ghunt.helpers import auth, calendar as gcalendar, gmaps, playgames

@dataclass
class EmailLookup(Transform):
    name: ClassVar[str] = "Email Lookup"
    description: ClassVar[str] = "Extract usernames, websites, images, locations and events from email using GHunt"
    input_types: ClassVar[List[str]] = ["Email"]
    output_types: ClassVar[List[str]] = ["Username", "Website", "Image", "Location", "Event"]
    
    async def run(self, entity: Email, graph) -> List[Entity]:
        if not isinstance(entity, Email) or not (email_address := entity.properties.get("address")):
            return []
        
        status = StatusManager.get()
        operation_id = status.start_loading("Email Lookup")
        status.set_text("Email lookup started")
        
        try:
            async with get_httpx_client() as as_client:
                try:
                    ghunt_creds = await auth.load_and_auth(as_client)
                    people_pa = PeoplePaHttp(ghunt_creds)
                except Exception as e:
                    status.set_text(f"You're not authenticated, please authenticate first in GHunt")
                    return []
                
                is_found, target = await people_pa.people_lookup(as_client, email_address, params_template="max_details")
                
                if not is_found:
                    status.set_text("Email not found")
                    return []

                target.email = email_address
                await self._fetch_additional_data(target, ghunt_creds, as_client)
                entities = await self._process_ghunt_results(target, ghunt_creds, as_client)
                
                status.set_text(f"Email lookup complete - found {len(entities)} entities")
                return entities

        except Exception as e:
            status.set_text(f"Error during email lookup: {e}")
            print(f"Error during email lookup: {e}")
            return []
        finally:
            status.stop_loading(operation_id)

    async def _fetch_additional_data(self, target, ghunt_creds: GHuntCreds, as_client: httpx.AsyncClient):
        # Fetch Maps data
        err, stats, reviews, photos = await gmaps.get_reviews(as_client, target.personId)
        if not err or err not in ["failed", "private", "empty"]:
            target.maps_reviews = reviews
            target.maps_photos = photos
            target.maps_stats = stats

        # Fetch Calendar data
        cal_found, calendar, calendar_events = await gcalendar.fetch_all(ghunt_creds, as_client, target.email)
        if cal_found:
            target.calendar = calendar
            target.calendar_events = calendar_events

    def _create_entities(self, entity_type: str, **kwargs) -> Entity:
        entity_map = {
            "username": Username,
            "website": Website,
            "image": Image,
            "location": Location,
            "event": Event
        }
        return entity_map[entity_type](properties={**kwargs, "source": "EmailToEntities transform"})

    async def _process_ghunt_results(self, target, ghunt_creds: GHuntCreds, as_client: httpx.AsyncClient) -> List[Entity]:
        entities = []

        # Process profile photos
        if hasattr(target, 'profilePhotos') and "PROFILE" in target.profilePhotos:
            photo = target.profilePhotos["PROFILE"]
            if not photo.isDefault:
                entities.append(self._create_entities("image", url=photo.url, title="Profile Photo", 
                                                   description="Google Account profile photo", image=photo.url))

        if hasattr(target, 'coverPhotos') and "PROFILE" in target.coverPhotos:
            cover = target.coverPhotos["PROFILE"]
            if not cover.isDefault:
                entities.append(self._create_entities("image", url=cover.url, title="Cover Photo", 
                                                   description="Google Account cover photo", image=cover.url))

        # Process usernames from services
        if hasattr(target, 'inAppReachability') and "PROFILE" in target.inAppReachability:
            for app in target.inAppReachability["PROFILE"].apps:
                entities.append(self._create_entities("username", username=target.personId, platform=app))

        # Process Play Games data
        player_results = await playgames.search_player(ghunt_creds, as_client, target.email)
        if player_results:
            player = player_results[0]
            _, player_details = await playgames.get_player(ghunt_creds, as_client, player.id)

            entities.append(self._create_entities("username", username=player.name, platform="Play Games",
                                               link=f"https://play.google.com/games/profile/{player.id}"))
            # if last played game, create an event
            if player_details.profile.last_played_app:
                entities.append(self._create_entities("event", name=player_details.profile.last_played_app.app_name, 
                    description=f"Last played game: {player_details.profile.last_played_app.app_name}",
                    start_date=player_details.profile.last_played_app.timestamp_millis, 
                    end_date=player_details.profile.last_played_app.timestamp_millis, 
                    add_to_timeline=True))
                
            if player.avatar_url:
                entities.append(self._create_entities("image", url=player.avatar_url, title="Play Games Avatar",
                                                   description=f"Play Games profile avatar for {player.name}", 
                                                   image=player.avatar_url))
            
            if player_details and hasattr(player_details, 'linked_accounts'):
                for account in player_details.linked_accounts:
                    if hasattr(account, 'platform') and hasattr(account, 'username'):
                        entities.append(self._create_entities("username", username=account.username, 
                                                           platform=account.platform,
                                                           link=getattr(account, 'url', "")))

        # Process Maps data
        if hasattr(target, 'maps_reviews') or hasattr(target, 'maps_photos'):
            reviews_and_photos = getattr(target, 'maps_reviews', []) + getattr(target, 'maps_photos', [])
            for item in reviews_and_photos:
                if hasattr(item, 'location'):
                    loc = item.location
                    if hasattr(loc, 'position') and loc.position:
                        notes = f"Visited {loc.name} at date {item.date.strftime('%Y-%m-%d %H:%M')}\n"
                        if hasattr(item, 'comment'):
                            notes += f"\nComment: {item.comment}\n"
                        if hasattr(item, 'rating'):
                            notes += f"\nRating: {item.rating}/5"
                            
                        entities.append(self._create_entities("location", 
                            latitude=str(loc.position.latitude),
                            longitude=str(loc.position.longitude),
                            notes=notes
                        ))

        # Process Calendar events
        if hasattr(target, 'calendar_events') and target.calendar_events:
            for event in target.calendar_events.items:
                try:
                    start_date = end_date = ""
                    
                    # Handle start date
                    if hasattr(event, 'start'):
                        if hasattr(event.start, 'date_time') and event.start.date_time:
                            start_date = event.start.date_time.strftime("%Y-%m-%d %H:%M")
                        elif hasattr(event.start, 'date') and event.start.date:
                            start_date = f"{event.start.date} 00:00"
                    
                    # Handle end date
                    if hasattr(event, 'end'):
                        if hasattr(event.end, 'date_time') and event.end.date_time:
                            end_date = event.end.date_time.strftime("%Y-%m-%d %H:%M")
                        elif hasattr(event.end, 'date') and event.end.date:
                            end_date = f"{event.end.date} 23:59"
                    
                    description = getattr(event, 'description', "")
                    if description is None:
                        description = ""
                    
                    # Calculate duration only if we have both dates
                    if start_date and end_date:
                        try:
                            start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
                            end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M")
                        except ValueError:
                            pass  # Skip duration calculation if date parsing fails
                    
                    entities.append(self._create_entities("event",
                        name=getattr(event, 'summary', "Untitled Event"),
                        description=description,
                        start_date=start_dt,
                        end_date=end_dt,
                        add_to_timeline=True
                    ))
                except Exception as e:
                    print(f"Failed to process calendar event: {e}")
                    continue

        return entities 