# Generated by the protocol buffer compiler.  DO NOT EDIT!
# sources: steammessages_webui_friends.proto
# plugin: python-betterproto
from dataclasses import dataclass
from typing import List

import betterproto

from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from steammessages_base import CMsgIPAddress, CCDDBAppDetailCommon, CClanMatchEventByRange

    from steammessages_clientserver_friends import CMsgClientFriendsList


@dataclass
class CHelpRequestLogs_UploadUserApplicationLog_Request(betterproto.Message):
    appid: int = betterproto.uint32_field(1)
    log_type: str = betterproto.string_field(2)
    version_string: str = betterproto.string_field(3)
    log_contents: str = betterproto.string_field(4)


@dataclass
class CHelpRequestLogs_UploadUserApplicationLog_Response(betterproto.Message):
    id: int = betterproto.uint64_field(1)


@dataclass
class CMsgClientAppMinutesPlayedData(betterproto.Message):
    minutes_played: List[
        "CMsgClientAppMinutesPlayedData_AppMinutesPlayedData"
    ] = betterproto.message_field(1)


@dataclass
class CMsgClientAppMinutesPlayedData_AppMinutesPlayedData(betterproto.Message):
    app_id: int = betterproto.uint32_field(1)
    forever: int = betterproto.int32_field(2)
    last_two_weeks: int = betterproto.int32_field(3)


@dataclass
class CCommunity_GetApps_Request(betterproto.Message):
    appids: List[int] = betterproto.int32_field(1)
    language: int = betterproto.uint32_field(2)


@dataclass
class CCommunity_GetApps_Response(betterproto.Message):
    apps: List["CCDDBAppDetailCommon"] = betterproto.message_field(1)


@dataclass
class CCommunity_GetAppRichPresenceLocalization_Request(betterproto.Message):
    appid: int = betterproto.int32_field(1)
    language: str = betterproto.string_field(2)


@dataclass
class CCommunity_GetAppRichPresenceLocalization_Response(betterproto.Message):
    appid: int = betterproto.int32_field(1)
    token_lists: List[
        "CCommunity_GetAppRichPresenceLocalization_Response_TokenList"
    ] = betterproto.message_field(2)


@dataclass
class CCommunity_GetAppRichPresenceLocalization_Response_Token(betterproto.Message):
    name: str = betterproto.string_field(1)
    value: str = betterproto.string_field(2)


@dataclass
class CCommunity_GetAppRichPresenceLocalization_Response_TokenList(betterproto.Message):
    language: str = betterproto.string_field(1)
    tokens: List[
        "CCommunity_GetAppRichPresenceLocalization_Response_Token"
    ] = betterproto.message_field(2)


@dataclass
class CCommunity_GetCommentThread_Request(betterproto.Message):
    steamid: float = betterproto.fixed64_field(1)
    comment_thread_type: int = betterproto.uint32_field(2)
    gidfeature: float = betterproto.fixed64_field(3)
    gidfeature2: float = betterproto.fixed64_field(4)
    commentthreadid: float = betterproto.fixed64_field(5)
    start: int = betterproto.int32_field(6)
    count: int = betterproto.int32_field(7)
    upvoters: int = betterproto.int32_field(8)
    include_deleted: bool = betterproto.bool_field(9)
    gidcomment: float = betterproto.fixed64_field(10)
    time_oldest: int = betterproto.uint32_field(11)
    oldest_first: bool = betterproto.bool_field(12)


@dataclass
class CCommunity_Comment(betterproto.Message):
    gidcomment: float = betterproto.fixed64_field(1)
    steamid: float = betterproto.fixed64_field(2)
    timestamp: int = betterproto.uint32_field(3)
    text: str = betterproto.string_field(4)
    upvotes: int = betterproto.int32_field(5)
    hidden: bool = betterproto.bool_field(6)
    hidden_by_user: bool = betterproto.bool_field(7)
    deleted: bool = betterproto.bool_field(8)
    ipaddress: "CMsgIPAddress" = betterproto.message_field(9)
    total_hidden: int = betterproto.int32_field(10)
    upvoted_by_user: bool = betterproto.bool_field(11)


@dataclass
class CCommunity_GetCommentThread_Response(betterproto.Message):
    comments: List["CCommunity_Comment"] = betterproto.message_field(1)
    deleted_comments: List["CCommunity_Comment"] = betterproto.message_field(2)
    steamid: float = betterproto.fixed64_field(3)
    commentthreadid: float = betterproto.fixed64_field(4)
    start: int = betterproto.int32_field(5)
    count: int = betterproto.int32_field(6)
    total_count: int = betterproto.int32_field(7)
    upvotes: int = betterproto.int32_field(8)
    upvoters: List[int] = betterproto.uint32_field(9)
    user_subscribed: bool = betterproto.bool_field(10)
    user_upvoted: bool = betterproto.bool_field(11)
    answer_commentid: float = betterproto.fixed64_field(12)
    answer_actor: int = betterproto.uint32_field(13)
    answer_actor_rank: int = betterproto.int32_field(14)
    can_post: bool = betterproto.bool_field(15)


@dataclass
class CCommunity_PostCommentToThread_Request(betterproto.Message):
    steamid: float = betterproto.fixed64_field(1)
    comment_thread_type: int = betterproto.uint32_field(2)
    gidfeature: float = betterproto.fixed64_field(3)
    gidfeature2: float = betterproto.fixed64_field(4)
    text: str = betterproto.string_field(6)
    gidparentcomment: float = betterproto.fixed64_field(7)
    suppress_notifications: bool = betterproto.bool_field(8)


@dataclass
class CCommunity_PostCommentToThread_Response(betterproto.Message):
    gidcomment: float = betterproto.fixed64_field(1)
    commentthreadid: float = betterproto.fixed64_field(2)
    count: int = betterproto.int32_field(3)
    upvotes: int = betterproto.int32_field(4)


@dataclass
class CCommunity_DeleteCommentFromThread_Request(betterproto.Message):
    steamid: float = betterproto.fixed64_field(1)
    comment_thread_type: int = betterproto.uint32_field(2)
    gidfeature: float = betterproto.fixed64_field(3)
    gidfeature2: float = betterproto.fixed64_field(4)
    gidcomment: float = betterproto.fixed64_field(5)
    undelete: bool = betterproto.bool_field(6)


@dataclass
class CCommunity_DeleteCommentFromThread_Response(betterproto.Message):
    pass


@dataclass
class CCommunity_RateCommentThread_Request(betterproto.Message):
    commentthreadtype: str = betterproto.string_field(1)
    steamid: int = betterproto.uint64_field(2)
    gidfeature: int = betterproto.uint64_field(3)
    gidfeature2: int = betterproto.uint64_field(4)
    gidcomment: int = betterproto.uint64_field(5)
    rate_up: bool = betterproto.bool_field(6)
    suppress_notifications: bool = betterproto.bool_field(7)


@dataclass
class CCommunity_RateCommentThread_Response(betterproto.Message):
    gidcomment: int = betterproto.uint64_field(1)
    commentthreadid: int = betterproto.uint64_field(2)
    count: int = betterproto.uint32_field(3)
    upvotes: int = betterproto.uint32_field(4)
    has_upvoted: bool = betterproto.bool_field(5)


@dataclass
class CCommunity_GetCommentThreadRatings_Request(betterproto.Message):
    commentthreadtype: str = betterproto.string_field(1)
    steamid: int = betterproto.uint64_field(2)
    gidfeature: int = betterproto.uint64_field(3)
    gidfeature2: int = betterproto.uint64_field(4)
    gidcomment: int = betterproto.uint64_field(5)
    max_results: int = betterproto.uint32_field(6)


@dataclass
class CCommunity_GetCommentThreadRatings_Response(betterproto.Message):
    commentthreadid: int = betterproto.uint64_field(1)
    gidcomment: int = betterproto.uint64_field(2)
    upvotes: int = betterproto.uint32_field(3)
    has_upvoted: bool = betterproto.bool_field(4)
    upvoter_accountids: List[int] = betterproto.uint32_field(5)


@dataclass
class CCommunity_RateClanAnnouncement_Request(betterproto.Message):
    announcementid: int = betterproto.uint64_field(1)
    vote_up: bool = betterproto.bool_field(2)


@dataclass
class CCommunity_RateClanAnnouncement_Response(betterproto.Message):
    pass


@dataclass
class CCommunity_GetClanAnnouncementVoteForUser_Request(betterproto.Message):
    announcementid: int = betterproto.uint64_field(1)


@dataclass
class CCommunity_GetClanAnnouncementVoteForUser_Response(betterproto.Message):
    voted_up: bool = betterproto.bool_field(1)
    voted_down: bool = betterproto.bool_field(2)


@dataclass
class CAppPriority(betterproto.Message):
    priority: int = betterproto.uint32_field(1)
    appid: List[int] = betterproto.uint32_field(2)


@dataclass
class CCommunity_GetUserPartnerEventNews_Request(betterproto.Message):
    count: int = betterproto.uint32_field(1)
    offset: int = betterproto.uint32_field(2)
    rtime32_start_time: int = betterproto.uint32_field(3)
    rtime32_end_time: int = betterproto.uint32_field(4)
    language_preference: List[int] = betterproto.uint32_field(5)
    filter_event_type: List[int] = betterproto.int32_field(6)
    filter_to_appid: bool = betterproto.bool_field(7)
    app_list: List["CAppPriority"] = betterproto.message_field(8)
    count_after: int = betterproto.uint32_field(9)
    count_before: int = betterproto.uint32_field(10)


@dataclass
class CCommunity_GetUserPartnerEventNews_Response(betterproto.Message):
    results: List["CClanMatchEventByRange"] = betterproto.message_field(1)


@dataclass
class CCommunity_GetBestEventsForUser_Request(betterproto.Message):
    include_steam_blog: bool = betterproto.bool_field(1)
    filter_to_played_within_days: int = betterproto.uint32_field(2)


@dataclass
class CCommunity_PartnerEventResult(betterproto.Message):
    clanid: int = betterproto.uint32_field(1)
    event_gid: float = betterproto.fixed64_field(2)
    announcement_gid: float = betterproto.fixed64_field(3)
    appid: int = betterproto.uint32_field(4)
    possible_takeover: bool = betterproto.bool_field(5)
    rtime32_last_modified: int = betterproto.uint32_field(6)
    user_app_priority: int = betterproto.int32_field(7)


@dataclass
class CCommunity_GetBestEventsForUser_Response(betterproto.Message):
    results: List["CCommunity_PartnerEventResult"] = betterproto.message_field(1)


@dataclass
class CCommunity_ClearUserPartnerEventsAppPriorities_Request(betterproto.Message):
    pass


@dataclass
class CCommunity_ClearUserPartnerEventsAppPriorities_Response(betterproto.Message):
    pass


@dataclass
class CCommunity_PartnerEventsAppPriority(betterproto.Message):
    appid: int = betterproto.uint32_field(1)
    user_app_priority: int = betterproto.int32_field(2)


@dataclass
class CCommunity_GetUserPartnerEventsAppPriorities_Request(betterproto.Message):
    pass


@dataclass
class CCommunity_GetUserPartnerEventsAppPriorities_Response(betterproto.Message):
    priorities: List["CCommunity_PartnerEventsAppPriority"] = betterproto.message_field(
        1
    )


@dataclass
class CCommunity_ClearSinglePartnerEventsAppPriority_Request(betterproto.Message):
    appid: int = betterproto.uint32_field(1)


@dataclass
class CCommunity_ClearSinglePartnerEventsAppPriority_Response(betterproto.Message):
    pass


@dataclass
class CCommunity_PartnerEventsShowMoreForApp_Request(betterproto.Message):
    appid: int = betterproto.uint32_field(1)


@dataclass
class CCommunity_PartnerEventsShowMoreForApp_Response(betterproto.Message):
    pass


@dataclass
class CCommunity_PartnerEventsShowLessForApp_Request(betterproto.Message):
    appid: int = betterproto.uint32_field(1)


@dataclass
class CCommunity_PartnerEventsShowLessForApp_Response(betterproto.Message):
    pass


@dataclass
class CCommunity_MarkPartnerEventsForUser_Request(betterproto.Message):
    markings: List[
        "CCommunity_MarkPartnerEventsForUser_Request_PartnerEventMarking"
    ] = betterproto.message_field(1)


@dataclass
class CCommunity_MarkPartnerEventsForUser_Request_PartnerEventMarking(
    betterproto.Message
):
    clanid: int = betterproto.uint32_field(1)
    event_gid: float = betterproto.fixed64_field(2)
    display_location: int = betterproto.int32_field(3)
    mark_shown: bool = betterproto.bool_field(4)
    mark_read: bool = betterproto.bool_field(5)


@dataclass
class CCommunity_MarkPartnerEventsForUser_Response(betterproto.Message):
    pass


@dataclass
class CProductImpressionsFromClient_Notification(betterproto.Message):
    impressions: List[
        "CProductImpressionsFromClient_Notification_Impression"
    ] = betterproto.message_field(1)


@dataclass
class CProductImpressionsFromClient_Notification_Impression(betterproto.Message):
    type: int = betterproto.int32_field(1)
    appid: int = betterproto.uint32_field(2)
    num_impressions: int = betterproto.uint32_field(3)


@dataclass
class CFriendsListCategory(betterproto.Message):
    groupid: int = betterproto.uint32_field(1)
    name: str = betterproto.string_field(2)
    accountid_members: List[int] = betterproto.uint32_field(3)


@dataclass
class CFriendsList_GetCategories_Request(betterproto.Message):
    pass


@dataclass
class CFriendsList_GetCategories_Response(betterproto.Message):
    categories: List["CFriendsListCategory"] = betterproto.message_field(1)


@dataclass
class CFriendsListFavoriteEntry(betterproto.Message):
    accountid: int = betterproto.uint32_field(1)
    clanid: int = betterproto.uint32_field(2)
    chat_group_id: int = betterproto.uint64_field(3)


@dataclass
class CFriendsList_GetFavorites_Request(betterproto.Message):
    pass


@dataclass
class CFriendsList_GetFavorites_Response(betterproto.Message):
    favorites: List["CFriendsListFavoriteEntry"] = betterproto.message_field(1)


@dataclass
class CFriendsList_SetFavorites_Request(betterproto.Message):
    favorites: List["CFriendsListFavoriteEntry"] = betterproto.message_field(1)


@dataclass
class CFriendsList_SetFavorites_Response(betterproto.Message):
    pass


@dataclass
class CFriendsList_FavoritesChanged_Notification(betterproto.Message):
    favorites: List["CFriendsListFavoriteEntry"] = betterproto.message_field(1)


@dataclass
class CFriendsList_GetFriendsList_Request(betterproto.Message):
    pass


@dataclass
class CFriendsList_GetFriendsList_Response(betterproto.Message):
    friendslist: "CMsgClientFriendsList" = betterproto.message_field(1)


@dataclass
class CMsgClientUCMEnumerateUserPublishedFiles(betterproto.Message):
    app_id: int = betterproto.uint32_field(1)
    start_index: int = betterproto.uint32_field(2)
    sort_order: int = betterproto.uint32_field(3)


@dataclass
class CMsgClientUCMEnumerateUserPublishedFilesResponse(betterproto.Message):
    eresult: int = betterproto.int32_field(1)
    published_files: List[
        "CMsgClientUCMEnumerateUserPublishedFilesResponse_PublishedFileId"
    ] = betterproto.message_field(2)
    total_results: int = betterproto.uint32_field(3)


@dataclass
class CMsgClientUCMEnumerateUserPublishedFilesResponse_PublishedFileId(
    betterproto.Message
):
    published_file_id: float = betterproto.fixed64_field(1)


@dataclass
class CMsgClientUCMEnumerateUserSubscribedFiles(betterproto.Message):
    app_id: int = betterproto.uint32_field(1)
    start_index: int = betterproto.uint32_field(2)
    list_type: int = betterproto.uint32_field(3)
    matching_file_type: int = betterproto.uint32_field(4)
    count: int = betterproto.uint32_field(5)


@dataclass
class CMsgClientUCMEnumerateUserSubscribedFilesResponse(betterproto.Message):
    eresult: int = betterproto.int32_field(1)
    subscribed_files: List[
        "CMsgClientUCMEnumerateUserSubscribedFilesResponse_PublishedFileId"
    ] = betterproto.message_field(2)
    total_results: int = betterproto.uint32_field(3)


@dataclass
class CMsgClientUCMEnumerateUserSubscribedFilesResponse_PublishedFileId(
    betterproto.Message
):
    published_file_id: float = betterproto.fixed64_field(1)
    rtime32_subscribed: float = betterproto.fixed32_field(2)


@dataclass
class CMsgClientUCMPublishedFileDeleted(betterproto.Message):
    published_file_id: float = betterproto.fixed64_field(1)
    app_id: int = betterproto.uint32_field(2)


@dataclass
class CMsgClientWorkshopItemInfoRequest(betterproto.Message):
    app_id: int = betterproto.uint32_field(1)
    last_time_updated: int = betterproto.uint32_field(2)
    workshop_items: List[
        "CMsgClientWorkshopItemInfoRequest_WorkshopItem"
    ] = betterproto.message_field(3)


@dataclass
class CMsgClientWorkshopItemInfoRequest_WorkshopItem(betterproto.Message):
    published_file_id: float = betterproto.fixed64_field(1)
    time_updated: int = betterproto.uint32_field(2)


@dataclass
class CMsgClientWorkshopItemInfoResponse(betterproto.Message):
    eresult: int = betterproto.int32_field(1)
    update_time: int = betterproto.uint32_field(2)
    workshop_items: List[
        "CMsgClientWorkshopItemInfoResponse_WorkshopItemInfo"
    ] = betterproto.message_field(3)
    private_items: List[float] = betterproto.fixed64_field(4)


@dataclass
class CMsgClientWorkshopItemInfoResponse_WorkshopItemInfo(betterproto.Message):
    published_file_id: float = betterproto.fixed64_field(1)
    time_updated: int = betterproto.uint32_field(2)
    manifest_id: float = betterproto.fixed64_field(3)
    is_legacy: bool = betterproto.bool_field(4)


@dataclass
class CMsgClientUCMGetPublishedFilesForUser(betterproto.Message):
    app_id: int = betterproto.uint32_field(1)
    creator_steam_id: float = betterproto.fixed64_field(2)
    required_tags: List[str] = betterproto.string_field(3)
    excluded_tags: List[str] = betterproto.string_field(4)
    start_index: int = betterproto.uint32_field(5)


@dataclass
class CMsgClientUCMGetPublishedFilesForUserResponse(betterproto.Message):
    eresult: int = betterproto.int32_field(1)
    published_files: List[
        "CMsgClientUCMGetPublishedFilesForUserResponse_PublishedFileId"
    ] = betterproto.message_field(2)
    total_results: int = betterproto.uint32_field(3)


@dataclass
class CMsgClientUCMGetPublishedFilesForUserResponse_PublishedFileId(
    betterproto.Message
):
    published_file_id: float = betterproto.fixed64_field(1)


@dataclass
class CMsgCREEnumeratePublishedFiles(betterproto.Message):
    app_id: int = betterproto.uint32_field(1)
    query_type: int = betterproto.int32_field(2)
    start_index: int = betterproto.uint32_field(3)
    days: int = betterproto.uint32_field(4)
    count: int = betterproto.uint32_field(5)
    tags: List[str] = betterproto.string_field(6)
    user_tags: List[str] = betterproto.string_field(7)
    matching_file_type: int = betterproto.uint32_field(8)


@dataclass
class CMsgCREEnumeratePublishedFilesResponse(betterproto.Message):
    eresult: int = betterproto.int32_field(1)
    published_files: List[
        "CMsgCREEnumeratePublishedFilesResponse_PublishedFileId"
    ] = betterproto.message_field(2)
    total_results: int = betterproto.uint32_field(3)


@dataclass
class CMsgCREEnumeratePublishedFilesResponse_PublishedFileId(betterproto.Message):
    published_file_id: float = betterproto.fixed64_field(1)
    votes_for: int = betterproto.int32_field(2)
    votes_against: int = betterproto.int32_field(3)
    reports: int = betterproto.int32_field(4)
    score: float = betterproto.float_field(5)


@dataclass
class CMsgGameServerPingSample(betterproto.Message):
    my_ip: float = betterproto.fixed32_field(1)
    gs_app_id: int = betterproto.int32_field(2)
    gs_samples: List["CMsgGameServerPingSample_Sample"] = betterproto.message_field(3)


@dataclass
class CMsgGameServerPingSample_Sample(betterproto.Message):
    ip: float = betterproto.fixed32_field(1)
    avg_ping_ms: int = betterproto.uint32_field(2)
    stddev_ping_ms_x10: int = betterproto.uint32_field(3)


@dataclass
class CClan_RespondToClanInvite_Request(betterproto.Message):
    steamid: float = betterproto.fixed64_field(1)
    accept: bool = betterproto.bool_field(2)


@dataclass
class CClan_RespondToClanInvite_Response(betterproto.Message):
    pass


@dataclass
class CVoiceChat_RequestOneOnOneChat_Request(betterproto.Message):
    steamid_partner: float = betterproto.fixed64_field(1)


@dataclass
class CVoiceChat_RequestOneOnOneChat_Response(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)


@dataclass
class CVoiceChat_OneOnOneChatRequested_Notification(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    steamid_partner: float = betterproto.fixed64_field(2)


@dataclass
class CVoiceChat_AnswerOneOnOneChat_Request(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    steamid_partner: float = betterproto.fixed64_field(2)
    accepted_request: bool = betterproto.bool_field(3)


@dataclass
class CVoiceChat_AnswerOneOnOneChat_Response(betterproto.Message):
    pass


@dataclass
class CVoiceChat_OneOnOneChatRequestResponse_Notification(betterproto.Message):
    voicechat_id: float = betterproto.fixed64_field(1)
    steamid_partner: float = betterproto.fixed64_field(2)
    accepted_request: bool = betterproto.bool_field(3)


@dataclass
class CVoiceChat_EndOneOnOneChat_Request(betterproto.Message):
    steamid_partner: float = betterproto.fixed64_field(1)


@dataclass
class CVoiceChat_EndOneOnOneChat_Response(betterproto.Message):
    pass


@dataclass
class CVoiceChat_LeaveOneOnOneChat_Request(betterproto.Message):
    steamid_partner: float = betterproto.fixed64_field(1)
    voice_chatid: float = betterproto.fixed64_field(2)


@dataclass
class CVoiceChat_LeaveOneOnOneChat_Response(betterproto.Message):
    pass


@dataclass
class CVoiceChat_UserJoinedVoiceChat_Notification(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    user_steamid: float = betterproto.fixed64_field(2)
    chatid: int = betterproto.uint64_field(3)
    one_on_one_steamid_lower: float = betterproto.fixed64_field(4)
    one_on_one_steamid_higher: float = betterproto.fixed64_field(5)
    chat_group_id: int = betterproto.uint64_field(6)
    user_sessionid: int = betterproto.uint32_field(7)


@dataclass
class CVoiceChat_UserVoiceStatus_Notification(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    user_steamid: float = betterproto.fixed64_field(2)
    user_muted_mic_locally: bool = betterproto.bool_field(3)
    user_muted_output_locally: bool = betterproto.bool_field(4)
    user_has_no_mic_for_session: bool = betterproto.bool_field(5)
    user_webaudio_sample_rate: int = betterproto.int32_field(6)


@dataclass
class CVoiceChat_AllMembersStatus_Notification(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    users: List["CVoiceChat_UserVoiceStatus_Notification"] = betterproto.message_field(
        2
    )


@dataclass
class CVoiceChat_UpdateVoiceChatWebRTCData_Request(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    ip_webrtc_server: int = betterproto.uint32_field(2)
    port_webrtc_server: int = betterproto.uint32_field(3)
    ip_webrtc_client: int = betterproto.uint32_field(4)
    port_webrtc_client: int = betterproto.uint32_field(5)
    ssrc_my_sending_stream: int = betterproto.uint32_field(6)
    user_agent: str = betterproto.string_field(7)
    has_audio_worklets_support: bool = betterproto.bool_field(8)


@dataclass
class CVoiceChat_UpdateVoiceChatWebRTCData_Response(betterproto.Message):
    send_client_voice_logs: bool = betterproto.bool_field(1)


@dataclass
class CVoiceChat_UploadClientVoiceChatLogs_Request(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    client_voice_logs_new_lines: str = betterproto.string_field(2)


@dataclass
class CVoiceChat_UploadClientVoiceChatLogs_Response(betterproto.Message):
    pass


@dataclass
class CVoiceChat_LeaveVoiceChat_Request(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)


@dataclass
class CVoiceChat_LeaveVoiceChat_Response(betterproto.Message):
    pass


@dataclass
class CVoiceChat_UserLeftVoiceChat_Notification(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    user_steamid: float = betterproto.fixed64_field(2)
    chatid: int = betterproto.uint64_field(3)
    one_on_one_steamid_lower: float = betterproto.fixed64_field(4)
    one_on_one_steamid_higher: float = betterproto.fixed64_field(5)
    chat_group_id: int = betterproto.uint64_field(6)
    user_sessionid: int = betterproto.uint32_field(7)


@dataclass
class CVoiceChat_VoiceChatEnded_Notification(betterproto.Message):
    voice_chatid: float = betterproto.fixed64_field(1)
    one_on_one_steamid_lower: float = betterproto.fixed64_field(2)
    one_on_one_steamid_higher: float = betterproto.fixed64_field(3)
    chatid: int = betterproto.uint64_field(4)
    chat_group_id: int = betterproto.uint64_field(5)


@dataclass
class CWebRTCClient_InitiateWebRTCConnection_Request(betterproto.Message):
    sdp: str = betterproto.string_field(1)


@dataclass
class CWebRTCClient_InitiateWebRTCConnection_Response(betterproto.Message):
    remote_description: str = betterproto.string_field(1)


@dataclass
class CWebRTC_WebRTCSessionConnected_Notification(betterproto.Message):
    ssrc: int = betterproto.uint32_field(1)
    client_ip: int = betterproto.uint32_field(2)
    client_port: int = betterproto.uint32_field(3)
    server_ip: int = betterproto.uint32_field(4)
    server_port: int = betterproto.uint32_field(5)


@dataclass
class CWebRTC_WebRTCUpdateRemoteDescription_Notification(betterproto.Message):
    remote_description: str = betterproto.string_field(1)
    remote_description_version: int = betterproto.uint64_field(2)
    ssrcs_to_accountids: List[
        "CWebRTC_WebRTCUpdateRemoteDescription_Notification_CSSRCToAccountIDMapping"
    ] = betterproto.message_field(3)


@dataclass
class CWebRTC_WebRTCUpdateRemoteDescription_Notification_CSSRCToAccountIDMapping(
    betterproto.Message
):
    ssrc: int = betterproto.uint32_field(1)
    accountid: int = betterproto.uint32_field(2)


@dataclass
class CWebRTCClient_AcknowledgeUpdatedRemoteDescription_Request(betterproto.Message):
    ip_webrtc_server: int = betterproto.uint32_field(1)
    port_webrtc_server: int = betterproto.uint32_field(2)
    ip_webrtc_session_client: int = betterproto.uint32_field(3)
    port_webrtc_session_client: int = betterproto.uint32_field(4)
    remote_description_version: int = betterproto.uint64_field(5)


@dataclass
class CWebRTCClient_AcknowledgeUpdatedRemoteDescription_Response(betterproto.Message):
    pass


@dataclass
class CMobilePerAccount_GetSettings_Request(betterproto.Message):
    pass


@dataclass
class CMobilePerAccount_GetSettings_Response(betterproto.Message):
    has_settings: bool = betterproto.bool_field(4)
    allow_sale_push: bool = betterproto.bool_field(2)
    allow_wishlist_push: bool = betterproto.bool_field(3)
    chat_notification_level: int = betterproto.uint32_field(5)
    notify_direct_chat: bool = betterproto.bool_field(6)
    notify_group_chat: bool = betterproto.bool_field(7)
    allow_event_push: bool = betterproto.bool_field(8)


@dataclass
class CMobilePerAccount_SetSettings_Request(betterproto.Message):
    allow_sale_push: bool = betterproto.bool_field(2)
    allow_wishlist_push: bool = betterproto.bool_field(3)
    chat_notification_level: int = betterproto.uint32_field(4)
    notify_direct_chat: bool = betterproto.bool_field(5)
    notify_group_chat: bool = betterproto.bool_field(6)
    allow_event_push: bool = betterproto.bool_field(7)


@dataclass
class CMobilePerAccount_SetSettings_Response(betterproto.Message):
    pass


@dataclass
class CMobileDevice_RegisterMobileDevice_Request(betterproto.Message):
    deviceid: str = betterproto.string_field(1)
    language: str = betterproto.string_field(2)
    push_enabled: bool = betterproto.bool_field(3)
    app_version: str = betterproto.string_field(4)
    os_version: str = betterproto.string_field(5)
    device_model: str = betterproto.string_field(6)
    twofactor_device_identifier: str = betterproto.string_field(7)
    mobile_app: int = betterproto.int32_field(8)


@dataclass
class CMobileDevice_RegisterMobileDevice_Response(betterproto.Message):
    unique_deviceid: int = betterproto.uint32_field(2)


@dataclass
class CMobileDevice_DeregisterMobileDevice_Notification(betterproto.Message):
    deviceid: str = betterproto.string_field(1)


@dataclass
class UnknownProto(betterproto.Message):
    pass
